
/* keymaster::V4_0::Keymaster4Device::Keymaster4Device(keymaster_security_level_t) */

void __thiscall
keymaster::V4_0::Keymaster4Device::Keymaster4Device
          (Keymaster4Device *this,long *param_2,undefined4 param_3)

{
  long lVar1;
  int iVar2;
  undefined4 uVar3;
  undefined8 *puVar4;
  KeymasterUtils *pKVar5;
  undefined8 *puVar6;
  ulong uVar7;
  long lVar8;
  ulong *local_120;
  undefined8 uStack_118;
  char *local_110;
  bool local_104 [4];
  ulong local_100;
  undefined8 uStack_f8;
  char *local_f0;
  undefined8 local_e8;
  undefined8 local_e0;
  undefined8 uStack_d8;
  undefined8 local_d0;
  undefined8 local_c8;
  undefined8 local_c0;
  ulong local_b0 [2];
  undefined8 *local_a0;
  undefined8 uStack_98;
  undefined8 uStack_90;
  undefined8 uStack_88;
  undefined8 local_80;
  undefined8 uStack_78;
  undefined8 uStack_70;
  undefined4 uStack_68;
  undefined4 local_64;
  undefined4 uStack_60;
  undefined8 uStack_5c;
  long local_48;
  
  lVar1 = tpidr_el0;
  local_48 = *(long *)(lVar1 + 0x28);
  lVar8 = param_2[2];
  *(long *)this = lVar8;
  *(long *)(this + *(long *)(lVar8 + -0x18)) = param_2[3];
  lVar8 = param_2[1];
  *(long *)this = lVar8;
  *(long *)(this + *(long *)(lVar8 + -0x18)) = param_2[4];
  lVar8 = *param_2;
  *(long *)this = lVar8;
  *(long *)(this + *(long *)(lVar8 + -0x18)) = param_2[5];
  puVar4 = operator_new(0x38);
  *puVar4 = &PTR__KeymasterHalDevice_00121430;
  pKVar5 = operator_new(0x10);
  keymasterutils::KeymasterUtils::KeymasterUtils(pKVar5,param_3);
  puVar4[2] = pKVar5;
  puVar6 = operator_new(8);
  puVar4[5] = 0;
  puVar4[3] = puVar6;
  puVar4[4] = puVar4 + 5;
  *puVar6 = &PTR__KeymasterBuffer_00121450;
  puVar4[6] = 0;
  *(undefined4 *)(puVar4 + 1) = param_3;
  *(undefined8 **)(this + 8) = puVar4;
  local_104[0] = false;
  *(undefined4 *)(this + 0x10) = param_3;
  local_a0 = operator_new(0x20);
  builtin_strncpy((char *)((long)local_a0 + 0x17),"ty_patch",8);
  builtin_strncpy((char *)((long)local_a0 + 0xf),"n.securi",8);
  local_a0[1] = 0x6e6f69737265762e;
  *local_a0 = 0x646c6975622e6f72;
  *(undefined1 *)((long)local_a0 + 0x1f) = 0;
  local_b0[1] = 0x1f;
  local_b0[0] = 0x21;
  uVar7 = android::base::WaitForPropertyCreation(local_b0,0x7fffffffffffffff);
  if ((uVar7 & 1) == 0) {
LAB_0010d2e4:
    if ((local_b0[0] & 1) != 0) {
      operator_delete(local_a0);
    }
LAB_0010d2f4:
    __android_log_assert
              (&DAT_0010a131,"android.hardware.keymaster@4.0-impl","Android property not present");
LAB_0010d310:
    __android_log_assert
              (&DAT_0010a131,"android.hardware.keymaster@4.0-impl","get_date_support failed");
  }
  else {
    local_f0 = operator_new(0x20);
    builtin_strncpy(local_f0,"ro.vendor.build.security_patch",0x1f);
    uStack_f8 = 0x1e;
    local_100 = 0x21;
    uVar7 = android::base::WaitForPropertyCreation(&local_100,0x7fffffffffffffff);
    if ((uVar7 & 1) == 0) {
      if ((local_100 & 1) != 0) {
        operator_delete(local_f0);
      }
      goto LAB_0010d2e4;
    }
    local_110 = operator_new(0x20);
    builtin_strncpy(local_110,"ro.build.version.release",0x19);
    uStack_118 = 0x18;
    local_120 = (ulong *)0x21;
    uVar7 = android::base::WaitForPropertyCreation(&local_120,0x7fffffffffffffff);
    if (((ulong)local_120 & 1) == 0) {
      if ((local_100 & 1) != 0) goto LAB_0010d1e4;
LAB_0010d1c4:
      if ((local_b0[0] & 1) != 0) goto LAB_0010d1f4;
LAB_0010d1cc:
      if ((uVar7 & 1) != 0) goto LAB_0010d200;
      goto LAB_0010d2f4;
    }
    operator_delete(local_110);
    if ((local_100 & 1) == 0) goto LAB_0010d1c4;
LAB_0010d1e4:
    operator_delete(local_f0);
    if ((local_b0[0] & 1) == 0) goto LAB_0010d1cc;
LAB_0010d1f4:
    operator_delete(local_a0);
    if ((uVar7 & 1) == 0) goto LAB_0010d2f4;
LAB_0010d200:
    local_120 = (ulong *)0x0;
    uStack_118 = 0;
    local_c0 = 0;
    uStack_d8 = 0;
    local_e0 = 0;
    local_c8 = 0;
    local_d0 = 0;
    uStack_f8 = 0;
    local_100 = 0;
    local_e8 = 0;
    local_f0 = (char *)0x0;
    iVar2 = keymasterdevice::KeymasterHalDevice::get_date_support
                      (*(KeymasterHalDevice **)(this + 8),local_104);
    if (iVar2 != 0) goto LAB_0010d310;
    local_100 = CONCAT44(local_100._4_4_,0x300002c1);
    uVar3 = GetOsVersion();
    uStack_f8 = CONCAT44(uStack_f8._4_4_,uVar3);
    uStack_5c = 0;
    uStack_60 = 0;
    uStack_78 = 0;
    local_80 = 0;
    uStack_68 = 0;
    local_64 = 0;
    uStack_70 = 0;
    uStack_98 = 0;
    local_a0 = (undefined8 *)0x0;
    uStack_88 = 0;
    uStack_90 = 0;
    local_e8 = CONCAT44(local_e8._4_4_,0x300002c2);
    local_b0[1] = 0;
    local_b0[0] = 0;
    property_get(&DAT_00109b60,local_b0,&DAT_0010a475);
    uVar3 = GetPatchlevel((char *)local_b0);
    local_e0 = CONCAT44(local_e0._4_4_,uVar3);
    local_d0 = CONCAT44(local_d0._4_4_,0x300002ce);
    uVar3 = GetVendorPatchlevel(local_104[0]);
    local_120 = &local_100;
    local_c8 = CONCAT44(local_c8._4_4_,uVar3);
    uStack_118 = 3;
    iVar2 = keymasterdevice::KeymasterHalDevice::configure
                      (*(KeymasterHalDevice **)(this + 8),(keymaster_key_param_set_t *)&local_120);
    if (iVar2 == 0) {
      if (*(long *)(lVar1 + 0x28) == local_48) {
        return;
      }
      goto LAB_0010d348;
    }
  }
  __android_log_assert(&DAT_0010a131,"android.hardware.keymaster@4.0-impl","Configure failed");
LAB_0010d348:
                    /* WARNING: Subroutine does not return */
  __stack_chk_fail();
}

