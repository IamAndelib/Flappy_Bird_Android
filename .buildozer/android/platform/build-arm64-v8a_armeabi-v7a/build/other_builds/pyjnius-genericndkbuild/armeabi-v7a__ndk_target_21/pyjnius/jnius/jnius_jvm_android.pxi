# on android, rely on SDL to get the JNI env
cdef extern JNIEnv *WebView_AndroidGetJNIEnv()


cdef JNIEnv *get_platform_jnienv() except NULL:
    return <JNIEnv*>WebView_AndroidGetJNIEnv()
