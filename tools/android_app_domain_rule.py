"""Add one exact trusted host to an explicitly named app's Rethink rule list."""
import argparse
import re
import shlex
from android_setup_ui import adb, snapshot


def tap(tree, resource_id):
    matches = [n for n in tree.iter('node')
               if n.get('resource-id') == 'com.celzero.bravedns:id/' + resource_id
               and n.get('enabled') == 'true']
    if len(matches) != 1:
        raise RuntimeError(f'Expected one {resource_id}, found {len(matches)}')
    n = matches[0]
    v = list(map(int, re.findall(r'\d+', n.get('bounds', ''))))
    if len(v) != 4 or v[2] <= v[0] or v[3] <= v[1]:
        raise RuntimeError('Control has no visible area')
    adb('shell', 'input', 'tap', str((v[0]+v[2])//2), str((v[1]+v[3])//2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-name', required=True)
    p.add_argument('--host', required=True)
    a = p.parse_args()
    if not re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)+', a.host) or a.host.endswith('.cn'):
        raise RuntimeError('Only exact non-.cn hostnames are accepted')
    label = 'destination-trust-' + a.host.replace('.', '-')
    tree = snapshot(label + '-list-before')
    fields = [n for n in tree.iter('node') if n.get('resource-id') ==
              'com.celzero.bravedns:id/search_src_text']
    if len(fields) != 1 or fields[0].get('text') != a.app_name + ': Search domain names':
        raise RuntimeError('The expected app-specific domain rule list is not open')
    if any(n.get('text') == a.host for n in tree.iter('node')):
        raise RuntimeError('Host already exists; inspect its status instead')
    tap(tree, 'cda_add_fab')
    tree = snapshot(label + '-dialog')
    chip = next(n for n in tree.iter('node') if n.get('resource-id') ==
                'com.celzero.bravedns:id/dacd_domain_chip')
    if chip.get('checked') != 'true':
        tap(tree, 'dacd_domain_chip')
        tree = snapshot(label + '-exact-domain')
    field = next(n for n in tree.iter('node') if n.get('resource-id') ==
                 'com.celzero.bravedns:id/dacd_domain_edit_text')
    if field.get('text') not in ('Enter Domain', ''):
        raise RuntimeError('Domain field is not empty')
    tap(tree, 'dacd_domain_edit_text')
    adb('shell', 'input', 'text', shlex.quote(a.host))
    tree = snapshot(label + '-entered')
    if not any(n.get('resource-id') == 'com.celzero.bravedns:id/dacd_domain_edit_text'
               and n.get('text') == a.host for n in tree.iter('node')):
        raise RuntimeError('Entered hostname does not match')
    tap(tree, 'dacd_trust_btn')
    tree = snapshot(label + '-saved')
    tap(tree, 'dacd_cancel_btn')
    tree = snapshot(label + '-list-after')
    rows = [n for n in tree.iter('node') if n.get('resource-id') ==
            'com.celzero.bravedns:id/custom_domain_container']
    matching = [n for n in rows if any(c.get('text') == a.host for c in n.iter('node'))]
    if len(matching) != 1 or not any(c.get('text', '').startswith('Trust ')
                                    for c in matching[0].iter('node')):
        raise RuntimeError('Trusted rule was not visible after saving')
    print(f'Confirmed {a.app_name}: trusted exact host {a.host}', flush=True)


if __name__ == '__main__':
    main()
