#!/usr/bin/env python3
"""Inspect an A/B OTA locally for the exact reader and bounded partition scope.

Passing this inspection is NOT install readiness: signature trust, AVB, live
layout, color hardware, restoration and explicit install approval are separate.
Never invokes adb/fastboot or extracts files onto the device.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class Rejected(ValueError):
    pass


def varint(data, position):
    value = 0
    for shift in range(0, 70, 7):
        if position >= len(data):
            raise Rejected('Truncated protobuf integer')
        byte = data[position]
        position += 1
        value |= (byte & 127) << shift
        if not byte & 128:
            return value, position
    raise Rejected('Oversized protobuf integer')


def fields(data):
    result = {}
    position = 0
    while position < len(data):
        tag, position = varint(data, position)
        number, kind = tag >> 3, tag & 7
        if not number:
            raise Rejected('Invalid protobuf field')
        if kind == 0:
            value, position = varint(data, position)
        elif kind in (1, 5):
            width = 8 if kind == 1 else 4
            value = data[position:position + width]
            if len(value) != width:
                raise Rejected('Truncated fixed protobuf field')
            position += width
        elif kind == 2:
            length, position = varint(data, position)
            if length > len(data) - position:
                raise Rejected('Protobuf field outside metadata')
            value = data[position:position + length]
            position += length
        else:
            raise Rejected('Unsupported protobuf wire format')
        result.setdefault(number, []).append(value)
    return result


def one(mapping, number, default=None):
    values = mapping.get(number, [])
    if len(values) > 1:
        raise Rejected('Duplicate singular metadata field')
    return values[0] if values else default


def inspect(path, role):
    profile = json.loads((ROOT / 'preparation/target-profile.json').read_text())
    expected_sdk = profile['stock_sdk'] if role == 'stock' else profile['android_sdk']
    allowed = set(profile['stock_ota_partitions'] if role == 'stock' else profile['allowed_lineage_partitions'])
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise Rejected('Duplicate ZIP entries')
        metadata_info = archive.getinfo('META-INF/com/android/metadata')
        if metadata_info.file_size > 1024 * 1024:
            raise Rejected('Oversized package metadata')
        metadata = {}
        for line in archive.read(metadata_info).decode().splitlines():
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            if key in metadata:
                raise Rejected('Duplicate OTA metadata key')
            metadata[key] = value
        if metadata.get('pre-device') != profile['model']:
            raise Rejected('Wrong hardware target: ' + metadata.get('pre-device', '(missing)'))
        if metadata.get('ota-type') != 'AB':
            raise Rejected('Only A/B packages are in this inspection scope')
        if metadata.get('post-sdk-level') != str(expected_sdk):
            raise Rejected('Unexpected Android SDK for selected baseline')
        with archive.open('payload.bin') as payload:
            header = payload.read(24)
            if len(header) != 24 or header[:4] != b'CrAU':
                raise Rejected('Invalid payload header')
            major, size, signature_size = struct.unpack('>QQI', header[4:])
            if major != 2 or not 0 < size <= 32 * 1024 * 1024:
                raise Rejected('Unsupported payload version or metadata size')
            raw = payload.read(size)
            if len(raw) != size:
                raise Rejected('Truncated payload manifest')
        manifest = fields(raw)
        if one(manifest, 12, 0) != 0:
            raise Rejected('Incremental payload is unsuitable as the first installation asset')
        if one(manifest, 16, 0):
            raise Rejected('Partial-update payload requires additional state review')
        partitions = []
        seen = set()
        for raw_part in manifest.get(13, []):
            part = fields(raw_part)
            name = one(part, 1, b'').decode('ascii')
            if not name or name in seen or name not in allowed:
                raise Rejected('Unsupported, protected or duplicate partition: ' + name)
            seen.add(name)
            if 6 in part:
                raise Rejected('Payload depends on a previous partition: ' + name)
            info = fields(one(part, 7, b''))
            image_size, image_hash = one(info, 1), one(info, 2, b'')
            if not isinstance(image_size, int) or image_size <= 0 or len(image_hash) != 32:
                raise Rejected('Missing final image size/hash: ' + name)
            if name in profile['stock_logical_partition_bytes']:
                category = 'logical'
            else:
                category = 'physical'
                capacities = [profile['physical_partition_bytes'].get(name + '_' + slot, 0) for slot in ['a', 'b']]
                if not all(image_size <= limit for limit in capacities):
                    raise Rejected('Image exceeds physical slot capacity: ' + name)
            operation_types = []
            for op in part.get(8, []):
                kind = one(fields(op), 1)
                if kind not in {0, 1, 6, 7, 8}:
                    raise Rejected('Unsupported/source-dependent operation in ' + name)
                operation_types.append(kind)
            partitions.append({'name': name, 'bytes': image_size, 'sha256': image_hash.hex(),
                               'category': category, 'operation_types': sorted(set(operation_types))})
        if not partitions:
            raise Rejected('No final partitions in payload')
        logical_total = sum(p['bytes'] for p in partitions if p['category'] == 'logical')
        if logical_total > profile['dynamic_group_bytes']:
            raise Rejected('Logical images exceed the known stock dynamic group capacity')
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    digest = h.hexdigest()
    known_stock_integrity = False
    if role == 'stock':
        stock = json.loads((ROOT / 'work/stock-firmware-validation-2026-11-11.json').read_text())
        known_stock_integrity = digest == stock['archive_sha256']
        if not known_stock_integrity:
            raise Rejected('Stock package differs from the validated archive')
    return {'offline_metadata_result': 'accepted_for_further_review', 'role': role,
            'device': metadata['pre-device'], 'sdk': expected_sdk, 'zip_sha256': digest,
            'known_validated_stock_archive': known_stock_integrity, 'partitions': partitions,
            'logical_image_bytes': logical_total, 'payload_max_timestamp': one(manifest, 14),
            'payload_metadata_signature_bytes': signature_size,
            'new_signature_or_avb_verification_performed': False,
            'install_ready': False, 'device_operation_performed': False,
            'remaining_checks': ['trusted release signing and full payload integrity',
                                 'AVB/rollback and boot/recovery pairing', 'live partition/snapshot layout',
                                 'exact color-model integration and restore route', 'explicit install approval']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--role', choices=['stock', 'lineage'], default='lineage')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    try:
        result = inspect(args.package, args.role)
    except (Rejected, KeyError, UnicodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({'offline_metadata_result': 'rejected', 'reason': str(exc),
                          'install_ready': False, 'device_operation_performed': False}, indent=2))
        raise SystemExit(2)
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
