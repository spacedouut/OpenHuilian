package com.shenju.uparser;

import com.shenju.uparser.model.UpPartitionInfo;
import com.shenju.uparser.model.anc.AncCalRespParam;
import com.shenju.uparser.model.anc.BaseAncCalRespParam;
import com.shenju.uparser.model.anc.CurveAncAssist;
import com.shenju.uparser.model.anc.CurveAncReference;
import com.shenju.uparser.model.eq.Eq2Data;
import com.shenju.uparser.model.eq.EqCoeffAnc;
import com.shenju.uparser.model.eq.EqConfigPoint;
import java.util.ArrayList;

/* loaded from: classes2.dex */
public class UparserJni {
    public static final String TAG_EQ2P = "EQ2P";
    public static final String TAG_FIRM = "FIRM";
    public static final String TAG_OTAP = "OTAP";
    public static final String TAG_PSMP = "PSMP";
    public static final String TAG_TONE = "TONE";

    public native int ancGetAncCofficent(EqConfigPoint eqConfigPoint, EqCoeffAnc eqCoeffAnc);

    public native int ancGetAncRefAssistCurve(BaseAncCalRespParam baseAncCalRespParam, CurveAncReference curveAncReference, CurveAncAssist curveAncAssist);

    public native int ancGetFfRefCurve(AncCalRespParam ancCalRespParam, CurveAncReference curveAncReference);

    public native int eqCurveGetFreqResp(int i, byte b, ArrayList<Float> arrayList, ArrayList<Float> arrayList2, ArrayList<Float> arrayList3, boolean z);

    public native void eqCurveSetGainRange(double d, double d2);

    public native int eqCurveSetSect(int i, byte b, ArrayList<EqConfigPoint> arrayList);

    public native byte[] eqGetAllBytes(Eq2Data eq2Data);

    public native int eqParseFromBytes(byte[] bArr, int i, Eq2Data eq2Data);

    public native int eqParseFromEq2File(String str, Eq2Data eq2Data);

    public native int eqSaveEq2File(Eq2Data eq2Data, String str);

    public native void upDeinit(long j);

    public native byte[] upGetAllBytes(long j);

    public native long upInit(String str);

    public native long upInitByBytes(byte[] bArr);

    public native UpPartitionInfo upPartitionGet(long j, String str, boolean z);

    public native byte[] upPartitionGetData(long j, String str);

    public native int upPartitionKeep(long j, UpPartitionInfo upPartitionInfo);

    public native int upPartitionSet(long j, UpPartitionInfo upPartitionInfo);

    public native int upSave(long j, String str);

    static {
        System.loadLibrary("uparser-lib");
    }
}
