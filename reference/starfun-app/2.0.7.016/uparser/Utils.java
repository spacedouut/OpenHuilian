package com.shenju.uparser;

import android.content.Context;
import android.os.Build;
import android.os.Environment;
import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;

/* loaded from: classes2.dex */
public class Utils {
    private static final String TAG = "Utils";

    /* JADX WARN: Multi-variable type inference failed */
    /* JADX WARN: Type inference failed for: r0v10 */
    /* JADX WARN: Type inference failed for: r0v13 */
    /* JADX WARN: Type inference failed for: r0v14 */
    /* JADX WARN: Type inference failed for: r0v15 */
    /* JADX WARN: Type inference failed for: r0v2 */
    /* JADX WARN: Type inference failed for: r0v20 */
    /* JADX WARN: Type inference failed for: r0v21 */
    /* JADX WARN: Type inference failed for: r0v3 */
    /* JADX WARN: Type inference failed for: r0v4, types: [java.io.OutputStream] */
    /* JADX WARN: Type inference failed for: r0v5 */
    /* JADX WARN: Type inference failed for: r0v8 */
    /* JADX WARN: Type inference failed for: r0v9 */
    public static void copyFileFromAssets(Context context, String str, String str2) throws Throwable {
        BufferedInputStream bufferedInputStream;
        if (str.isEmpty() || str2.isEmpty()) {
            return;
        }
        ?? r0 = 0;
        bufferedOutputStream = null;
        bufferedOutputStream = null;
        BufferedOutputStream bufferedOutputStream = null;
        BufferedOutputStream bufferedOutputStream2 = null;
        r0 = 0;
        r0 = 0;
        try {
            try {
                try {
                    bufferedInputStream = new BufferedInputStream(context.getAssets().open(str));
                    try {
                        BufferedOutputStream bufferedOutputStream3 = new BufferedOutputStream(new FileOutputStream(new File(str2)));
                        try {
                            byte[] bArr = new byte[1024];
                            while (true) {
                                int i = bufferedInputStream.read(bArr);
                                r0 = -1;
                                if (i == -1) {
                                    break;
                                } else {
                                    bufferedOutputStream3.write(bArr, 0, i);
                                }
                            }
                            bufferedOutputStream3.close();
                            bufferedInputStream.close();
                        } catch (FileNotFoundException e) {
                            e = e;
                            bufferedOutputStream = bufferedOutputStream3;
                            e.printStackTrace();
                            bufferedOutputStream.close();
                            bufferedInputStream.close();
                            r0 = bufferedOutputStream;
                        } catch (IOException e2) {
                            e = e2;
                            bufferedOutputStream2 = bufferedOutputStream3;
                            e.printStackTrace();
                            bufferedOutputStream2.close();
                            bufferedInputStream.close();
                            r0 = bufferedOutputStream2;
                        } catch (Throwable th) {
                            th = th;
                            r0 = bufferedOutputStream3;
                            try {
                                r0.close();
                                bufferedInputStream.close();
                            } catch (IOException e3) {
                                e3.printStackTrace();
                            }
                            throw th;
                        }
                    } catch (FileNotFoundException e4) {
                        e = e4;
                    } catch (IOException e5) {
                        e = e5;
                    }
                } catch (IOException e6) {
                    e6.printStackTrace();
                }
            } catch (FileNotFoundException e7) {
                e = e7;
                bufferedInputStream = null;
            } catch (IOException e8) {
                e = e8;
                bufferedInputStream = null;
            } catch (Throwable th2) {
                th = th2;
                bufferedInputStream = null;
            }
        } catch (Throwable th3) {
            th = th3;
        }
    }

    public static void copyDirectoryFromAssets(Context context, String str, String str2) throws Throwable {
        if (str.isEmpty() || str2.isEmpty()) {
            return;
        }
        try {
            if (!new File(str2).exists()) {
                new File(str2).mkdirs();
            }
            for (String str3 : context.getAssets().list(str)) {
                String str4 = str + File.separator + str3;
                String str5 = str2 + File.separator + str3;
                if (new File(str4).isDirectory()) {
                    copyDirectoryFromAssets(context, str4, str5);
                } else {
                    copyFileFromAssets(context, str4, str5);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static float[] parseFloatsFromString(String str, String str2) {
        String[] strArrSplit = str.trim().toLowerCase().split(str2);
        float[] fArr = new float[strArrSplit.length];
        for (int i = 0; i < strArrSplit.length; i++) {
            fArr[i] = Float.parseFloat(strArrSplit[i].trim());
        }
        return fArr;
    }

    public static long[] parseLongsFromString(String str, String str2) {
        String[] strArrSplit = str.trim().toLowerCase().split(str2);
        long[] jArr = new long[strArrSplit.length];
        for (int i = 0; i < strArrSplit.length; i++) {
            jArr[i] = Long.parseLong(strArrSplit[i].trim());
        }
        return jArr;
    }

    public static String getSDCardDirectory() {
        return Environment.getExternalStorageDirectory().getAbsolutePath();
    }

    public static boolean isSupportedNPU() {
        String str = Build.HARDWARE;
        return str.equalsIgnoreCase("kirin810") || str.equalsIgnoreCase("kirin990");
    }

    public static double cosineSimilarity(double[] dArr, double[] dArr2) {
        if (dArr == null || dArr2 == null || dArr.length == 0 || dArr2.length == 0 || dArr.length != dArr2.length) {
            return 0.0d;
        }
        double d = 0.0d;
        double d2 = 0.0d;
        double d3 = 0.0d;
        for (int i = 0; i < dArr.length; i++) {
            d2 += dArr[i] * dArr2[i];
            d += dArr[i] * dArr[i];
            d3 += dArr2[i] * dArr2[i];
        }
        if (d == 0.0d && d3 == 0.0d) {
            return 0.0d;
        }
        return d2 / (Math.sqrt(d) * Math.sqrt(d3));
    }
}
