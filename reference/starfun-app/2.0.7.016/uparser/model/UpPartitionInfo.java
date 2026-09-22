package com.shenju.uparser.model;

/* loaded from: classes2.dex */
public class UpPartitionInfo {
    public String tag = "";
    public int partitionLength = 0;
    public int offsetInFlash = 0;
    public byte[] partitionData = null;

    public String getTag() {
        return this.tag;
    }

    public void setTag(String str) {
        this.tag = str;
    }

    public int getPartitionLength() {
        return this.partitionLength;
    }

    public void setPartitionLength(int i) {
        this.partitionLength = i;
    }

    public int getOffsetInFlash() {
        return this.offsetInFlash;
    }

    public void setOffsetInFlash(int i) {
        this.offsetInFlash = i;
    }

    public byte[] getPartitionData() {
        return this.partitionData;
    }

    public void setPartitionData(byte[] bArr) {
        this.partitionData = bArr;
    }
}
