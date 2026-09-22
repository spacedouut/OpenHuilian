package com.shenju.uparser.model.eq;

import java.util.ArrayList;

/* loaded from: classes2.dex */
public class Eq2Data {
    private ArrayList<ArrayList<Eq2ItemData>> eqItemList = null;
    private byte[] extraData = null;
    private int extraDataLength = 0;

    public ArrayList<ArrayList<Eq2ItemData>> getEqItemList() {
        return this.eqItemList;
    }

    public void setEqItemList(ArrayList<ArrayList<Eq2ItemData>> arrayList) {
        this.eqItemList = arrayList;
    }

    public byte[] getExtraData() {
        return this.extraData;
    }

    public void setExtraData(byte[] bArr) {
        this.extraData = bArr;
    }

    public int getExtraDataLength() {
        return this.extraDataLength;
    }

    public void setExtraDataLength(int i) {
        this.extraDataLength = i;
    }
}
