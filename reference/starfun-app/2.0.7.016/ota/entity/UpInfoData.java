package com.shenju.ota.entity;

import cn.hutool.core.text.CharPool;
import java.util.Arrays;

/* loaded from: classes2.dex */
public class UpInfoData {
    public int firmwareLength;
    public int firmwarePosition;
    public byte[] indexByteArray;
    public int indexPosition;
    public int otaPosition;
    public int partitionNum;
    public byte[] upPartByteArrayWithIndex;
    public byte[] upPartByteArrayWithOutIndex;
    public String upSize;
    public String version;

    public String toString() {
        return "UpInfoData{indexPosition=" + this.indexPosition + ", indexByteArray=" + Arrays.toString(this.indexByteArray) + ", firmwarePosition=" + this.firmwarePosition + ", upPartByteArrayWithIndex=" + Arrays.toString(this.upPartByteArrayWithIndex) + ", upPartByteArrayWithOutIndex=" + Arrays.toString(this.upPartByteArrayWithOutIndex) + ", otaPosition=" + this.otaPosition + ", partitionNum=" + this.partitionNum + ", version='" + this.version + CharPool.SINGLE_QUOTE + '}';
    }
}
