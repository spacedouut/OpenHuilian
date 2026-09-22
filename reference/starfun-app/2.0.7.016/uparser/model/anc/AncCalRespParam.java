package com.shenju.uparser.model.anc;

import java.io.Serializable;
import java.util.ArrayList;

/* loaded from: classes2.dex */
public class AncCalRespParam extends BaseAncCalRespParam implements Serializable {
    public int delay;
    public double objGain;
    public ArrayList<Double> reqFreqList = new ArrayList<>();
    public ArrayList<Double> reqAmpList = new ArrayList<>();
    public int minimumPhase = 1;
}
