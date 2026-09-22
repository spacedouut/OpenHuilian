package com.shenju.ota.utils;

import com.shenju.uparser.UparserJni;
import com.shenju.uparser.model.UpPartitionInfo;

/* loaded from: classes2.dex */
public class UParseUtil {
    private static UParseUtil _instance;
    private final String TAG = "UParseUtil";
    public UparserJni upaserJni;

    private UParseUtil() {
        this.upaserJni = null;
        this.upaserJni = new UparserJni();
    }

    public static UParseUtil getInstance() {
        if (_instance == null) {
            synchronized (UParseUtil.class) {
                if (_instance == null) {
                    _instance = new UParseUtil();
                }
            }
        }
        return _instance;
    }

    private UpPartitionInfo getPartInfo(long j, String str, byte[] bArr) {
        UpPartitionInfo upPartitionInfo = new UpPartitionInfo();
        upPartitionInfo.setPartitionData(bArr);
        upPartitionInfo.setPartitionLength(bArr.length);
        upPartitionInfo.setTag(str);
        byte[] bArrUpPartitionGetData = this.upaserJni.upPartitionGetData(j, str);
        BtUtils.logBlueTooth("org data length:" + (bArrUpPartitionGetData == null ? 0 : bArrUpPartitionGetData.length));
        return upPartitionInfo;
    }

    public int savePartDataToUpFile(byte[] bArr, byte[] bArr2, byte[] bArr3, String str, String str2) {
        long jUpInit = this.upaserJni.upInit(str);
        BtUtils.logBlueTooth("upContext:" + jUpInit);
        if (bArr2 == null || bArr2.length == 0) {
            BtUtils.logBlueTooth("error: data is null.");
            return -3;
        }
        BtUtils.logBlueTooth("eq upPartitionSet:" + this.upaserJni.upPartitionSet(jUpInit, getPartInfo(jUpInit, "EQ2P", bArr2)));
        BtUtils.logBlueTooth("tone upPartitionSet:" + this.upaserJni.upPartitionSet(jUpInit, getPartInfo(jUpInit, "TONE", bArr3)));
        UpPartitionInfo upPartitionInfo = new UpPartitionInfo();
        upPartitionInfo.setPartitionData(bArr);
        upPartitionInfo.setPartitionLength(bArr.length);
        upPartitionInfo.setTag(UparserJni.TAG_OTAP);
        BtUtils.logBlueTooth("otap upPartitionKeep indexTable.length:" + bArr.length);
        int iUpPartitionKeep = this.upaserJni.upPartitionKeep(jUpInit, upPartitionInfo);
        BtUtils.logBlueTooth("otap upPartitionKeep:" + iUpPartitionKeep);
        if (iUpPartitionKeep == 0) {
            iUpPartitionKeep = this.upaserJni.upSave(jUpInit, str2);
            BtUtils.logBlueTooth("upSave:" + iUpPartitionKeep);
        }
        this.upaserJni.upDeinit(jUpInit);
        return iUpPartitionKeep;
    }
}
