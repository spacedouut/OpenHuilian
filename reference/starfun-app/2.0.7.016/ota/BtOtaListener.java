package com.shenju.ota;

import com.shenju.ota.entity.UpInfoData;

/* loaded from: classes2.dex */
public interface BtOtaListener {
    void onAllConditionsOk();

    void onConditionFail(int i);

    void onConnectDiffDev();

    void onSendMsg(byte[] bArr, int i);

    void onSyncProcess(int i, double d);

    void onUpFileParseFail();

    void onUpFileParseSuccess(UpInfoData upInfoData);

    void onUpGradeFail(int i);

    void onUpgradeProcess(boolean z, double d);

    void onUpgradeSuccess(String str);
}
