typedef unsigned char   undefined;

typedef unsigned char    bool;
typedef unsigned char    byte;
typedef unsigned int    dword;
typedef unsigned long long    GUID;
typedef pointer32 ImageBaseOffset32;

typedef long long    longlong;
typedef unsigned long long    qword;
typedef unsigned char    uchar;
typedef unsigned int    uint;
typedef unsigned long    ulong;
typedef unsigned long long    ulonglong;
typedef unsigned char    undefined1;
typedef unsigned short    undefined2;
typedef unsigned int    undefined4;
typedef unsigned long long    undefined8;
typedef unsigned short    ushort;
typedef unsigned short    wchar16;
typedef short    wchar_t;
typedef unsigned short    word;
#define unkbyte9   unsigned long long
#define unkbyte10   unsigned long long
#define unkbyte11   unsigned long long
#define unkbyte12   unsigned long long
#define unkbyte13   unsigned long long
#define unkbyte14   unsigned long long
#define unkbyte15   unsigned long long
#define unkbyte16   unsigned long long

#define unkuint9   unsigned long long
#define unkuint10   unsigned long long
#define unkuint11   unsigned long long
#define unkuint12   unsigned long long
#define unkuint13   unsigned long long
#define unkuint14   unsigned long long
#define unkuint15   unsigned long long
#define unkuint16   unsigned long long

#define unkint9   long long
#define unkint10   long long
#define unkint11   long long
#define unkint12   long long
#define unkint13   long long
#define unkint14   long long
#define unkint15   long long
#define unkint16   long long

#define unkfloat1   float
#define unkfloat2   float
#define unkfloat3   float
#define unkfloat5   double
#define unkfloat6   double
#define unkfloat7   double
#define unkfloat9   long double
#define unkfloat11   long double
#define unkfloat12   long double
#define unkfloat13   long double
#define unkfloat14   long double
#define unkfloat15   long double
#define unkfloat16   long double

#define BADSPACEBASE   void
#define code   void

typedef struct _s__RTTIBaseClassDescriptor _s__RTTIBaseClassDescriptor, *P_s__RTTIBaseClassDescriptor;

typedef struct _s__RTTIBaseClassDescriptor RTTIBaseClassDescriptor;

typedef RTTIBaseClassDescriptor *RTTIBaseClassDescriptor *32 __((image-base-relative));

typedef RTTIBaseClassDescriptor *32 __((image-base-relative)) *RTTIBaseClassDescriptor *32 __((image-base-relative)) *32 __((image-base-relative));

typedef struct PMD PMD, *PPMD;

struct PMD {
    int mdisp;
    int pdisp;
    int vdisp;
};

struct _s__RTTIBaseClassDescriptor {
    ImageBaseOffset32 pTypeDescriptor; // ref to TypeDescriptor (RTTI 0) for class
    dword numContainedBases; // count of extended classes in BaseClassArray (RTTI 2)
    struct PMD where; // member displacement structure
    dword attributes; // bit flags
    ImageBaseOffset32 pClassHierarchyDescriptor; // ref to ClassHierarchyDescriptor (RTTI 3) for class
};

typedef union IMAGE_RESOURCE_DIRECTORY_ENTRY_DirectoryUnion IMAGE_RESOURCE_DIRECTORY_ENTRY_DirectoryUnion, *PIMAGE_RESOURCE_DIRECTORY_ENTRY_DirectoryUnion;

typedef struct IMAGE_RESOURCE_DIRECTORY_ENTRY_DirectoryStruct IMAGE_RESOURCE_DIRECTORY_ENTRY_DirectoryStruct, *PIMAGE_RESOURCE_DIRECTORY_ENTRY_DirectoryStruct;

struct IMAGE_RESOURCE_DIRECTORY_ENTRY_DirectoryStruct {
    dword OffsetToDirectory:31;
    dword DataIsDirectory:1;
};

union IMAGE_RESOURCE_DIRECTORY_ENTRY_DirectoryUnion {
    dword OffsetToData;
    struct IMAGE_RESOURCE_DIRECTORY_ENTRY_DirectoryStruct IMAGE_RESOURCE_DIRECTORY_ENTRY_DirectoryStruct;
};

typedef struct _s__RTTIClassHierarchyDescriptor _s__RTTIClassHierarchyDescriptor, *P_s__RTTIClassHierarchyDescriptor;

struct _s__RTTIClassHierarchyDescriptor {
    dword signature;
    dword attributes; // bit flags
    dword numBaseClasses; // number of base classes (i.e. rtti1Count)
    RTTIBaseClassDescriptor *32 __((image-base-relative)) *32 __((image-base-relative)) pBaseClassArray; // ref to BaseClassArray (RTTI 2)
};

typedef struct _s__RTTICompleteObjectLocator _s__RTTICompleteObjectLocator, *P_s__RTTICompleteObjectLocator;

struct _s__RTTICompleteObjectLocator {
    dword signature;
    dword offset; // offset of vbtable within class
    dword cdOffset; // constructor displacement offset
    ImageBaseOffset32 pTypeDescriptor; // ref to TypeDescriptor (RTTI 0) for class
    ImageBaseOffset32 pClassDescriptor; // ref to ClassHierarchyDescriptor (RTTI 3)
};

typedef struct CLIENT_ID CLIENT_ID, *PCLIENT_ID;

struct CLIENT_ID {
    void *UniqueProcess;
    void *UniqueThread;
};

typedef struct _s__RTTIClassHierarchyDescriptor RTTIClassHierarchyDescriptor;

typedef struct _s__RTTICompleteObjectLocator RTTICompleteObjectLocator;

typedef ulonglong __uint64;

typedef struct tagMSG tagMSG, *PtagMSG;

typedef struct tagMSG MSG;

typedef struct HWND__ HWND__, *PHWND__;

typedef struct HWND__ *HWND;

typedef uint UINT;

typedef ulonglong UINT_PTR;

typedef UINT_PTR WPARAM;

typedef longlong LONG_PTR;

typedef LONG_PTR LPARAM;

typedef ulong DWORD;

typedef struct tagPOINT tagPOINT, *PtagPOINT;

typedef struct tagPOINT POINT;

typedef long LONG;

struct tagPOINT {
    LONG x;
    LONG y;
};

struct tagMSG {
    HWND hwnd;
    UINT message;
    WPARAM wParam;
    LPARAM lParam;
    DWORD time;
    POINT pt;
};

struct HWND__ {
    int unused;
};

typedef struct tagPAINTSTRUCT tagPAINTSTRUCT, *PtagPAINTSTRUCT;

typedef struct tagPAINTSTRUCT PAINTSTRUCT;

typedef struct HDC__ HDC__, *PHDC__;

typedef struct HDC__ *HDC;

typedef int BOOL;

typedef struct tagRECT tagRECT, *PtagRECT;

typedef struct tagRECT RECT;

typedef uchar BYTE;

struct HDC__ {
    int unused;
};

struct tagRECT {
    LONG left;
    LONG top;
    LONG right;
    LONG bottom;
};

struct tagPAINTSTRUCT {
    HDC hdc;
    BOOL fErase;
    RECT rcPaint;
    BOOL fRestore;
    BOOL fIncUpdate;
    BYTE rgbReserved[32];
};

typedef struct tagTRACKMOUSEEVENT tagTRACKMOUSEEVENT, *PtagTRACKMOUSEEVENT;

struct tagTRACKMOUSEEVENT {
    DWORD cbSize;
    DWORD dwFlags;
    HWND hwndTrack;
    DWORD dwHoverTime;
};

typedef struct tagWNDCLASSW tagWNDCLASSW, *PtagWNDCLASSW;

typedef struct tagWNDCLASSW WNDCLASSW;

typedef LONG_PTR LRESULT;

typedef LRESULT (*WNDPROC)(HWND, UINT, WPARAM, LPARAM);

typedef struct HINSTANCE__ HINSTANCE__, *PHINSTANCE__;

typedef struct HINSTANCE__ *HINSTANCE;

typedef struct HICON__ HICON__, *PHICON__;

typedef struct HICON__ *HICON;

typedef HICON HCURSOR;

typedef struct HBRUSH__ HBRUSH__, *PHBRUSH__;

typedef struct HBRUSH__ *HBRUSH;

typedef wchar_t WCHAR;

typedef WCHAR *LPCWSTR;

struct HBRUSH__ {
    int unused;
};

struct HICON__ {
    int unused;
};

struct tagWNDCLASSW {
    UINT style;
    WNDPROC lpfnWndProc;
    int cbClsExtra;
    int cbWndExtra;
    HINSTANCE hInstance;
    HICON hIcon;
    HCURSOR hCursor;
    HBRUSH hbrBackground;
    LPCWSTR lpszMenuName;
    LPCWSTR lpszClassName;
};

struct HINSTANCE__ {
    int unused;
};

typedef struct tagMSG *LPMSG;

typedef struct tagPAINTSTRUCT *LPPAINTSTRUCT;

typedef struct tagTRACKMOUSEEVENT *LPTRACKMOUSEEVENT;

typedef struct future_error future_error, *Pfuture_error;

struct future_error { // PlaceHolder Class Structure
};

typedef struct tagPIXELFORMATDESCRIPTOR tagPIXELFORMATDESCRIPTOR, *PtagPIXELFORMATDESCRIPTOR;

typedef ushort WORD;

struct tagPIXELFORMATDESCRIPTOR {
    WORD nSize;
    WORD nVersion;
    DWORD dwFlags;
    BYTE iPixelType;
    BYTE cColorBits;
    BYTE cRedBits;
    BYTE cRedShift;
    BYTE cGreenBits;
    BYTE cGreenShift;
    BYTE cBlueBits;
    BYTE cBlueShift;
    BYTE cAlphaBits;
    BYTE cAlphaShift;
    BYTE cAccumBits;
    BYTE cAccumRedBits;
    BYTE cAccumGreenBits;
    BYTE cAccumBlueBits;
    BYTE cAccumAlphaBits;
    BYTE cDepthBits;
    BYTE cStencilBits;
    BYTE cAuxBuffers;
    BYTE iLayerType;
    BYTE bReserved;
    DWORD dwLayerMask;
    DWORD dwVisibleMask;
    DWORD dwDamageMask;
};

typedef struct tagPIXELFORMATDESCRIPTOR PIXELFORMATDESCRIPTOR;

typedef DWORD LCTYPE;

typedef struct _OVERLAPPED _OVERLAPPED, *P_OVERLAPPED;

typedef ulonglong ULONG_PTR;

typedef union _union_540 _union_540, *P_union_540;

typedef void *HANDLE;

typedef struct _struct_541 _struct_541, *P_struct_541;

typedef void *PVOID;

struct _struct_541 {
    DWORD Offset;
    DWORD OffsetHigh;
};

union _union_540 {
    struct _struct_541 s;
    PVOID Pointer;
};

struct _OVERLAPPED {
    ULONG_PTR Internal;
    ULONG_PTR InternalHigh;
    union _union_540 u;
    HANDLE hEvent;
};

typedef struct _SECURITY_ATTRIBUTES _SECURITY_ATTRIBUTES, *P_SECURITY_ATTRIBUTES;

typedef void *LPVOID;

struct _SECURITY_ATTRIBUTES {
    DWORD nLength;
    LPVOID lpSecurityDescriptor;
    BOOL bInheritHandle;
};

typedef enum _FINDEX_INFO_LEVELS {
    FindExInfoStandard=0,
    FindExInfoBasic=1,
    FindExInfoMaxInfoLevel=2
} _FINDEX_INFO_LEVELS;

typedef struct _STARTUPINFOW _STARTUPINFOW, *P_STARTUPINFOW;

typedef WCHAR *LPWSTR;

typedef BYTE *LPBYTE;

struct _STARTUPINFOW {
    DWORD cb;
    LPWSTR lpReserved;
    LPWSTR lpDesktop;
    LPWSTR lpTitle;
    DWORD dwX;
    DWORD dwY;
    DWORD dwXSize;
    DWORD dwYSize;
    DWORD dwXCountChars;
    DWORD dwYCountChars;
    DWORD dwFillAttribute;
    DWORD dwFlags;
    WORD wShowWindow;
    WORD cbReserved2;
    LPBYTE lpReserved2;
    HANDLE hStdInput;
    HANDLE hStdOutput;
    HANDLE hStdError;
};

typedef struct _STARTUPINFOW *LPSTARTUPINFOW;

typedef struct _WIN32_FIND_DATAW _WIN32_FIND_DATAW, *P_WIN32_FIND_DATAW;

typedef struct _WIN32_FIND_DATAW *LPWIN32_FIND_DATAW;

typedef struct _FILETIME _FILETIME, *P_FILETIME;

typedef struct _FILETIME FILETIME;

struct _FILETIME {
    DWORD dwLowDateTime;
    DWORD dwHighDateTime;
};

struct _WIN32_FIND_DATAW {
    DWORD dwFileAttributes;
    FILETIME ftCreationTime;
    FILETIME ftLastAccessTime;
    FILETIME ftLastWriteTime;
    DWORD nFileSizeHigh;
    DWORD nFileSizeLow;
    DWORD dwReserved0;
    DWORD dwReserved1;
    WCHAR cFileName[260];
    WCHAR cAlternateFileName[14];
};

typedef enum _FILE_INFO_BY_HANDLE_CLASS {
    FileBasicInfo=0,
    FileStandardInfo=1,
    FileNameInfo=2,
    FileRenameInfo=3,
    FileDispositionInfo=4,
    FileAllocationInfo=5,
    FileEndOfFileInfo=6,
    FileStreamInfo=7,
    FileCompressionInfo=8,
    FileAttributeTagInfo=9,
    FileIdBothDirectoryInfo=10,
    FileIdBothDirectoryRestartInfo=11,
    FileIoPriorityHintInfo=12,
    FileRemoteProtocolInfo=13,
    MaximumFileInfoByHandleClass=14
} _FILE_INFO_BY_HANDLE_CLASS;

typedef enum _FILE_INFO_BY_HANDLE_CLASS FILE_INFO_BY_HANDLE_CLASS;

typedef union _RTL_RUN_ONCE _RTL_RUN_ONCE, *P_RTL_RUN_ONCE;

typedef union _RTL_RUN_ONCE *PRTL_RUN_ONCE;

typedef PRTL_RUN_ONCE LPINIT_ONCE;

union _RTL_RUN_ONCE {
    PVOID Ptr;
};

typedef struct _OVERLAPPED *LPOVERLAPPED;

typedef DWORD (*PTHREAD_START_ROUTINE)(LPVOID);

typedef PTHREAD_START_ROUTINE LPTHREAD_START_ROUTINE;

typedef struct _BY_HANDLE_FILE_INFORMATION _BY_HANDLE_FILE_INFORMATION, *P_BY_HANDLE_FILE_INFORMATION;

struct _BY_HANDLE_FILE_INFORMATION {
    DWORD dwFileAttributes;
    FILETIME ftCreationTime;
    FILETIME ftLastAccessTime;
    FILETIME ftLastWriteTime;
    DWORD dwVolumeSerialNumber;
    DWORD nFileSizeHigh;
    DWORD nFileSizeLow;
    DWORD nNumberOfLinks;
    DWORD nFileIndexHigh;
    DWORD nFileIndexLow;
};

typedef enum _FINDEX_SEARCH_OPS {
    FindExSearchNameMatch=0,
    FindExSearchLimitToDirectories=1,
    FindExSearchLimitToDevices=2,
    FindExSearchMaxSearchOp=3
} _FINDEX_SEARCH_OPS;

typedef enum _FINDEX_SEARCH_OPS FINDEX_SEARCH_OPS;

typedef struct _SECURITY_ATTRIBUTES *LPSECURITY_ATTRIBUTES;

typedef enum _FINDEX_INFO_LEVELS FINDEX_INFO_LEVELS;

typedef enum _GET_FILEEX_INFO_LEVELS {
    GetFileExInfoStandard=0,
    GetFileExMaxInfoLevel=1
} _GET_FILEEX_INFO_LEVELS;

typedef struct _BY_HANDLE_FILE_INFORMATION *LPBY_HANDLE_FILE_INFORMATION;

typedef enum _GET_FILEEX_INFO_LEVELS GET_FILEEX_INFO_LEVELS;

typedef struct _RTL_CRITICAL_SECTION _RTL_CRITICAL_SECTION, *P_RTL_CRITICAL_SECTION;

typedef struct _RTL_CRITICAL_SECTION *PRTL_CRITICAL_SECTION;

typedef PRTL_CRITICAL_SECTION LPCRITICAL_SECTION;

typedef struct _RTL_CRITICAL_SECTION_DEBUG _RTL_CRITICAL_SECTION_DEBUG, *P_RTL_CRITICAL_SECTION_DEBUG;

typedef struct _RTL_CRITICAL_SECTION_DEBUG *PRTL_CRITICAL_SECTION_DEBUG;

typedef struct _LIST_ENTRY _LIST_ENTRY, *P_LIST_ENTRY;

typedef struct _LIST_ENTRY LIST_ENTRY;

struct _RTL_CRITICAL_SECTION {
    PRTL_CRITICAL_SECTION_DEBUG DebugInfo;
    LONG LockCount;
    LONG RecursionCount;
    HANDLE OwningThread;
    HANDLE LockSemaphore;
    ULONG_PTR SpinCount;
};

struct _LIST_ENTRY {
    struct _LIST_ENTRY *Flink;
    struct _LIST_ENTRY *Blink;
};

struct _RTL_CRITICAL_SECTION_DEBUG {
    WORD Type;
    WORD CreatorBackTraceIndex;
    struct _RTL_CRITICAL_SECTION *CriticalSection;
    LIST_ENTRY ProcessLocksList;
    DWORD EntryCount;
    DWORD ContentionCount;
    DWORD Flags;
    WORD CreatorBackTraceIndexHigh;
    WORD SpareWORD;
};

typedef struct _EXCEPTION_POINTERS _EXCEPTION_POINTERS, *P_EXCEPTION_POINTERS;

typedef LONG (*PTOP_LEVEL_EXCEPTION_FILTER)(struct _EXCEPTION_POINTERS *);

typedef struct _EXCEPTION_RECORD _EXCEPTION_RECORD, *P_EXCEPTION_RECORD;

typedef struct _EXCEPTION_RECORD EXCEPTION_RECORD;

typedef EXCEPTION_RECORD *PEXCEPTION_RECORD;

typedef struct _CONTEXT _CONTEXT, *P_CONTEXT;

typedef struct _CONTEXT *PCONTEXT;

typedef ulonglong DWORD64;

typedef union _union_54 _union_54, *P_union_54;

typedef struct _M128A _M128A, *P_M128A;

typedef struct _M128A M128A;

typedef struct _XSAVE_FORMAT _XSAVE_FORMAT, *P_XSAVE_FORMAT;

typedef struct _XSAVE_FORMAT XSAVE_FORMAT;

typedef XSAVE_FORMAT XMM_SAVE_AREA32;

typedef struct _struct_55 _struct_55, *P_struct_55;

typedef ulonglong ULONGLONG;

typedef longlong LONGLONG;

struct _M128A {
    ULONGLONG Low;
    LONGLONG High;
};

struct _XSAVE_FORMAT {
    WORD ControlWord;
    WORD StatusWord;
    BYTE TagWord;
    BYTE Reserved1;
    WORD ErrorOpcode;
    DWORD ErrorOffset;
    WORD ErrorSelector;
    WORD Reserved2;
    DWORD DataOffset;
    WORD DataSelector;
    WORD Reserved3;
    DWORD MxCsr;
    DWORD MxCsr_Mask;
    M128A FloatRegisters[8];
    M128A XmmRegisters[16];
    BYTE Reserved4[96];
};

struct _struct_55 {
    M128A Header[2];
    M128A Legacy[8];
    M128A Xmm0;
    M128A Xmm1;
    M128A Xmm2;
    M128A Xmm3;
    M128A Xmm4;
    M128A Xmm5;
    M128A Xmm6;
    M128A Xmm7;
    M128A Xmm8;
    M128A Xmm9;
    M128A Xmm10;
    M128A Xmm11;
    M128A Xmm12;
    M128A Xmm13;
    M128A Xmm14;
    M128A Xmm15;
};

union _union_54 {
    XMM_SAVE_AREA32 FltSave;
    struct _struct_55 s;
};

struct _CONTEXT {
    DWORD64 P1Home;
    DWORD64 P2Home;
    DWORD64 P3Home;
    DWORD64 P4Home;
    DWORD64 P5Home;
    DWORD64 P6Home;
    DWORD ContextFlags;
    DWORD MxCsr;
    WORD SegCs;
    WORD SegDs;
    WORD SegEs;
    WORD SegFs;
    WORD SegGs;
    WORD SegSs;
    DWORD EFlags;
    DWORD64 Dr0;
    DWORD64 Dr1;
    DWORD64 Dr2;
    DWORD64 Dr3;
    DWORD64 Dr6;
    DWORD64 Dr7;
    DWORD64 Rax;
    DWORD64 Rcx;
    DWORD64 Rdx;
    DWORD64 Rbx;
    DWORD64 Rsp;
    DWORD64 Rbp;
    DWORD64 Rsi;
    DWORD64 Rdi;
    DWORD64 R8;
    DWORD64 R9;
    DWORD64 R10;
    DWORD64 R11;
    DWORD64 R12;
    DWORD64 R13;
    DWORD64 R14;
    DWORD64 R15;
    DWORD64 Rip;
    union _union_54 u;
    M128A VectorRegister[26];
    DWORD64 VectorControl;
    DWORD64 DebugControl;
    DWORD64 LastBranchToRip;
    DWORD64 LastBranchFromRip;
    DWORD64 LastExceptionToRip;
    DWORD64 LastExceptionFromRip;
};

struct _EXCEPTION_RECORD {
    DWORD ExceptionCode;
    DWORD ExceptionFlags;
    struct _EXCEPTION_RECORD *ExceptionRecord;
    PVOID ExceptionAddress;
    DWORD NumberParameters;
    ULONG_PTR ExceptionInformation[15];
};

struct _EXCEPTION_POINTERS {
    PEXCEPTION_RECORD ExceptionRecord;
    PCONTEXT ContextRecord;
};

typedef PTOP_LEVEL_EXCEPTION_FILTER LPTOP_LEVEL_EXCEPTION_FILTER;

typedef struct _MEMORY_BASIC_INFORMATION _MEMORY_BASIC_INFORMATION, *P_MEMORY_BASIC_INFORMATION;

typedef ULONG_PTR SIZE_T;

struct _MEMORY_BASIC_INFORMATION {
    PVOID BaseAddress;
    PVOID AllocationBase;
    DWORD AllocationProtect;
    SIZE_T RegionSize;
    DWORD State;
    DWORD Protect;
    DWORD Type;
};

typedef char CHAR;

typedef union _LARGE_INTEGER _LARGE_INTEGER, *P_LARGE_INTEGER;

typedef struct _struct_19 _struct_19, *P_struct_19;

typedef struct _struct_20 _struct_20, *P_struct_20;

struct _struct_20 {
    DWORD LowPart;
    LONG HighPart;
};

struct _struct_19 {
    DWORD LowPart;
    LONG HighPart;
};

union _LARGE_INTEGER {
    struct _struct_19 s;
    struct _struct_20 u;
    LONGLONG QuadPart;
};

typedef union _LARGE_INTEGER LARGE_INTEGER;

typedef struct _TOKEN_PRIVILEGES _TOKEN_PRIVILEGES, *P_TOKEN_PRIVILEGES;

typedef struct _LUID_AND_ATTRIBUTES _LUID_AND_ATTRIBUTES, *P_LUID_AND_ATTRIBUTES;

typedef struct _LUID_AND_ATTRIBUTES LUID_AND_ATTRIBUTES;

typedef struct _LUID _LUID, *P_LUID;

typedef struct _LUID LUID;

struct _LUID {
    DWORD LowPart;
    LONG HighPart;
};

struct _LUID_AND_ATTRIBUTES {
    LUID Luid;
    DWORD Attributes;
};

struct _TOKEN_PRIVILEGES {
    DWORD PrivilegeCount;
    LUID_AND_ATTRIBUTES Privileges[1];
};

typedef struct _RUNTIME_FUNCTION _RUNTIME_FUNCTION, *P_RUNTIME_FUNCTION;

struct _RUNTIME_FUNCTION {
    DWORD BeginAddress;
    DWORD EndAddress;
    DWORD UnwindData;
};

typedef struct _RUNTIME_FUNCTION *PRUNTIME_FUNCTION;

typedef enum _EXCEPTION_DISPOSITION {
    ExceptionContinueExecution=0,
    ExceptionContinueSearch=1,
    ExceptionNestedException=2,
    ExceptionCollidedUnwind=3
} _EXCEPTION_DISPOSITION;

typedef enum _EXCEPTION_DISPOSITION EXCEPTION_DISPOSITION;

typedef EXCEPTION_DISPOSITION (EXCEPTION_ROUTINE)(struct _EXCEPTION_RECORD *, PVOID, struct _CONTEXT *, PVOID);

typedef BYTE BOOLEAN;

typedef struct _M128A *PM128A;

typedef struct _UNWIND_HISTORY_TABLE_ENTRY _UNWIND_HISTORY_TABLE_ENTRY, *P_UNWIND_HISTORY_TABLE_ENTRY;

typedef struct _UNWIND_HISTORY_TABLE_ENTRY UNWIND_HISTORY_TABLE_ENTRY;

struct _UNWIND_HISTORY_TABLE_ENTRY {
    DWORD64 ImageBase;
    PRUNTIME_FUNCTION FunctionEntry;
};

typedef union _union_61 _union_61, *P_union_61;

typedef struct _struct_62 _struct_62, *P_struct_62;

struct _struct_62 {
    PM128A Xmm0;
    PM128A Xmm1;
    PM128A Xmm2;
    PM128A Xmm3;
    PM128A Xmm4;
    PM128A Xmm5;
    PM128A Xmm6;
    PM128A Xmm7;
    PM128A Xmm8;
    PM128A Xmm9;
    PM128A Xmm10;
    PM128A Xmm11;
    PM128A Xmm12;
    PM128A Xmm13;
    PM128A Xmm14;
    PM128A Xmm15;
};

union _union_61 {
    PM128A FloatingContext[16];
    struct _struct_62 s;
};

typedef union _union_63 _union_63, *P_union_63;

typedef ulonglong *PDWORD64;

typedef struct _struct_64 _struct_64, *P_struct_64;

struct _struct_64 {
    PDWORD64 Rax;
    PDWORD64 Rcx;
    PDWORD64 Rdx;
    PDWORD64 Rbx;
    PDWORD64 Rsp;
    PDWORD64 Rbp;
    PDWORD64 Rsi;
    PDWORD64 Rdi;
    PDWORD64 R8;
    PDWORD64 R9;
    PDWORD64 R10;
    PDWORD64 R11;
    PDWORD64 R12;
    PDWORD64 R13;
    PDWORD64 R14;
    PDWORD64 R15;
};

union _union_63 {
    PDWORD64 IntegerContext[16];
    struct _struct_64 s;
};

typedef struct _UNWIND_HISTORY_TABLE _UNWIND_HISTORY_TABLE, *P_UNWIND_HISTORY_TABLE;

typedef struct _UNWIND_HISTORY_TABLE *PUNWIND_HISTORY_TABLE;

struct _UNWIND_HISTORY_TABLE {
    DWORD Count;
    BYTE LocalHint;
    BYTE GlobalHint;
    BYTE Search;
    BYTE Once;
    DWORD64 LowAddress;
    DWORD64 HighAddress;
    UNWIND_HISTORY_TABLE_ENTRY Entry[12];
};

typedef struct _LUID *PLUID;

typedef CHAR *LPCSTR;

typedef struct _MEMORY_BASIC_INFORMATION *PMEMORY_BASIC_INFORMATION;

typedef CHAR *LPSTR;

typedef struct _KNONVOLATILE_CONTEXT_POINTERS _KNONVOLATILE_CONTEXT_POINTERS, *P_KNONVOLATILE_CONTEXT_POINTERS;

typedef struct _KNONVOLATILE_CONTEXT_POINTERS *PKNONVOLATILE_CONTEXT_POINTERS;

struct _KNONVOLATILE_CONTEXT_POINTERS {
    union _union_61 u;
    union _union_63 u2;
};

typedef EXCEPTION_ROUTINE *PEXCEPTION_ROUTINE;

typedef struct _TOKEN_PRIVILEGES *PTOKEN_PRIVILEGES;

typedef short SHORT;

typedef HANDLE *PHANDLE;

typedef struct IMAGE_DOS_HEADER IMAGE_DOS_HEADER, *PIMAGE_DOS_HEADER;

struct IMAGE_DOS_HEADER {
    char e_magic[2]; // Magic number
    word e_cblp; // Bytes of last page
    word e_cp; // Pages in file
    word e_crlc; // Relocations
    word e_cparhdr; // Size of header in paragraphs
    word e_minalloc; // Minimum extra paragraphs needed
    word e_maxalloc; // Maximum extra paragraphs needed
    word e_ss; // Initial (relative) SS value
    word e_sp; // Initial SP value
    word e_csum; // Checksum
    word e_ip; // Initial IP value
    word e_cs; // Initial (relative) CS value
    word e_lfarlc; // File address of relocation table
    word e_ovno; // Overlay number
    word e_res[4][4]; // Reserved words
    word e_oemid; // OEM identifier (for e_oeminfo)
    word e_oeminfo; // OEM information; e_oemid specific
    word e_res2[10][10]; // Reserved words
    dword e_lfanew; // File address of new exe header
    byte e_program[64]; // Actual DOS program
};

typedef long clock_t;

typedef longlong INT_PTR;

typedef struct DotNetPdbInfo DotNetPdbInfo, *PDotNetPdbInfo;

struct DotNetPdbInfo {
    char signature[4];
    GUID guid;
    dword age;
    char pdbpath[81];
};

typedef longlong fpos_t;

typedef struct tagPOINT *LPPOINT;

typedef struct HGLRC__ HGLRC__, *PHGLRC__;

typedef struct HGLRC__ *HGLRC;

struct HGLRC__ {
    int unused;
};

typedef DWORD *LPDWORD;

typedef DWORD *PDWORD;

typedef HINSTANCE HMODULE;

typedef HANDLE HLOCAL;

typedef BOOL *PBOOL;

typedef struct HMENU__ HMENU__, *PHMENU__;

typedef struct HMENU__ *HMENU;

struct HMENU__ {
    int unused;
};

typedef struct _FILETIME *LPFILETIME;

typedef INT_PTR (*FARPROC)(void);

typedef WORD ATOM;

typedef struct tagRECT *LPRECT;

typedef HANDLE HGLOBAL;

typedef BOOL *LPBOOL;

typedef void *LPCVOID;

typedef struct _IMAGE_RUNTIME_FUNCTION_ENTRY _IMAGE_RUNTIME_FUNCTION_ENTRY, *P_IMAGE_RUNTIME_FUNCTION_ENTRY;

struct _IMAGE_RUNTIME_FUNCTION_ENTRY {
    ImageBaseOffset32 BeginAddress;
    dword EndAddress; // Apply ImageBaseOffset32 to see reference
    ImageBaseOffset32 UnwindInfoAddressOrData;
};

typedef struct IMAGE_RESOURCE_DIRECTORY_ENTRY_NameStruct IMAGE_RESOURCE_DIRECTORY_ENTRY_NameStruct, *PIMAGE_RESOURCE_DIRECTORY_ENTRY_NameStruct;

struct IMAGE_RESOURCE_DIRECTORY_ENTRY_NameStruct {
    dword NameOffset:31;
    dword NameIsString:1;
};

typedef struct IMAGE_LOAD_CONFIG_CODE_INTEGRITY IMAGE_LOAD_CONFIG_CODE_INTEGRITY, *PIMAGE_LOAD_CONFIG_CODE_INTEGRITY;

struct IMAGE_LOAD_CONFIG_CODE_INTEGRITY {
    word Flags;
    word Catalog;
    dword CatalogOffset;
    dword Reserved;
};

typedef struct IMAGE_DEBUG_DIRECTORY IMAGE_DEBUG_DIRECTORY, *PIMAGE_DEBUG_DIRECTORY;

struct IMAGE_DEBUG_DIRECTORY {
    dword Characteristics;
    dword TimeDateStamp;
    word MajorVersion;
    word MinorVersion;
    dword Type;
    dword SizeOfData;
    dword AddressOfRawData;
    dword PointerToRawData;
};

typedef struct IMAGE_FILE_HEADER IMAGE_FILE_HEADER, *PIMAGE_FILE_HEADER;

struct IMAGE_FILE_HEADER {
    word Machine; // 34404
    word NumberOfSections;
    dword TimeDateStamp;
    dword PointerToSymbolTable;
    dword NumberOfSymbols;
    word SizeOfOptionalHeader;
    word Characteristics;
};

typedef struct IMAGE_LOAD_CONFIG_DIRECTORY64 IMAGE_LOAD_CONFIG_DIRECTORY64, *PIMAGE_LOAD_CONFIG_DIRECTORY64;

typedef enum IMAGE_GUARD_FLAGS {
    IMAGE_GUARD_CF_INSTRUMENTED=256,
    IMAGE_GUARD_CFW_INSTRUMENTED=512,
    IMAGE_GUARD_CF_FUNCTION_TABLE_PRESENT=1024,
    IMAGE_GUARD_SECURITY_COOKIE_UNUSED=2048,
    IMAGE_GUARD_PROTECT_DELAYLOAD_IAT=4096,
    IMAGE_GUARD_DELAYLOAD_IAT_IN_ITS_OWN_SECTION=8192,
    IMAGE_GUARD_CF_EXPORT_SUPPRESSION_INFO_PRESENT=16384,
    IMAGE_GUARD_CF_ENABLE_EXPORT_SUPPRESSION=32768,
    IMAGE_GUARD_CF_LONGJUMP_TABLE_PRESENT=65536,
    IMAGE_GUARD_RF_INSTRUMENTED=131072,
    IMAGE_GUARD_RF_ENABLE=262144,
    IMAGE_GUARD_RF_STRICT=524288,
    IMAGE_GUARD_CF_FUNCTION_TABLE_SIZE_MASK_1=268435456,
    IMAGE_GUARD_CF_FUNCTION_TABLE_SIZE_MASK_2=536870912,
    IMAGE_GUARD_CF_FUNCTION_TABLE_SIZE_MASK_4=1073741824,
    IMAGE_GUARD_CF_FUNCTION_TABLE_SIZE_MASK_8=2147483648
} IMAGE_GUARD_FLAGS;

struct IMAGE_LOAD_CONFIG_DIRECTORY64 {
    dword Size;
    dword TimeDateStamp;
    word MajorVersion;
    word MinorVersion;
    dword GlobalFlagsClear;
    dword GlobalFlagsSet;
    dword CriticalSectionDefaultTimeout;
    qword DeCommitFreeBlockThreshold;
    qword DeCommitTotalFreeThreshold;
    pointer64 LockPrefixTable;
    qword MaximumAllocationSize;
    qword VirtualMemoryThreshold;
    qword ProcessAffinityMask;
    dword ProcessHeapFlags;
    word CsdVersion;
    word DependentLoadFlags;
    pointer64 EditList;
    pointer64 SecurityCookie;
    pointer64 SEHandlerTable;
    qword SEHandlerCount;
    pointer64 GuardCFCCheckFunctionPointer;
    pointer64 GuardCFDispatchFunctionPointer;
    pointer64 GuardCFFunctionTable;
    qword GuardCFFunctionCount;
    enum IMAGE_GUARD_FLAGS GuardFlags;
    struct IMAGE_LOAD_CONFIG_CODE_INTEGRITY CodeIntegrity;
    pointer64 GuardAddressTakenIatEntryTable;
    qword GuardAddressTakenIatEntryCount;
    pointer64 GuardLongJumpTargetTable;
    qword GuardLongJumpTargetCount;
    pointer64 DynamicValueRelocTable;
    pointer64 CHPEMetadataPointer;
    pointer64 GuardRFFailureRoutine;
    pointer64 GuardRFFailureRoutineFunctionPointer;
    dword DynamicValueRelocTableOffset;
    word DynamicValueRelocTableSection;
    word Reserved1;
    pointer64 GuardRFVerifyStackPointerFunctionPointer;
    dword HotPatchTableOffset;
    dword Reserved2;
    qword Reserved3;
};

typedef struct IMAGE_RESOURCE_DIRECTORY_ENTRY IMAGE_RESOURCE_DIRECTORY_ENTRY, *PIMAGE_RESOURCE_DIRECTORY_ENTRY;

typedef union IMAGE_RESOURCE_DIRECTORY_ENTRY_NameUnion IMAGE_RESOURCE_DIRECTORY_ENTRY_NameUnion, *PIMAGE_RESOURCE_DIRECTORY_ENTRY_NameUnion;

union IMAGE_RESOURCE_DIRECTORY_ENTRY_NameUnion {
    struct IMAGE_RESOURCE_DIRECTORY_ENTRY_NameStruct IMAGE_RESOURCE_DIRECTORY_ENTRY_NameStruct;
    dword Name;
    word Id;
};

struct IMAGE_RESOURCE_DIRECTORY_ENTRY {
    union IMAGE_RESOURCE_DIRECTORY_ENTRY_NameUnion NameUnion;
    union IMAGE_RESOURCE_DIRECTORY_ENTRY_DirectoryUnion DirectoryUnion;
};

typedef struct IMAGE_OPTIONAL_HEADER64 IMAGE_OPTIONAL_HEADER64, *PIMAGE_OPTIONAL_HEADER64;

typedef struct IMAGE_DATA_DIRECTORY IMAGE_DATA_DIRECTORY, *PIMAGE_DATA_DIRECTORY;

struct IMAGE_DATA_DIRECTORY {
    ImageBaseOffset32 VirtualAddress;
    dword Size;
};

struct IMAGE_OPTIONAL_HEADER64 {
    word Magic;
    byte MajorLinkerVersion;
    byte MinorLinkerVersion;
    dword SizeOfCode;
    dword SizeOfInitializedData;
    dword SizeOfUninitializedData;
    ImageBaseOffset32 AddressOfEntryPoint;
    ImageBaseOffset32 BaseOfCode;
    pointer64 ImageBase;
    dword SectionAlignment;
    dword FileAlignment;
    word MajorOperatingSystemVersion;
    word MinorOperatingSystemVersion;
    word MajorImageVersion;
    word MinorImageVersion;
    word MajorSubsystemVersion;
    word MinorSubsystemVersion;
    dword Win32VersionValue;
    dword SizeOfImage;
    dword SizeOfHeaders;
    dword CheckSum;
    word Subsystem;
    word DllCharacteristics;
    qword SizeOfStackReserve;
    qword SizeOfStackCommit;
    qword SizeOfHeapReserve;
    qword SizeOfHeapCommit;
    dword LoaderFlags;
    dword NumberOfRvaAndSizes;
    struct IMAGE_DATA_DIRECTORY DataDirectory[16];
};

typedef struct IMAGE_SECTION_HEADER IMAGE_SECTION_HEADER, *PIMAGE_SECTION_HEADER;

typedef union Misc Misc, *PMisc;

typedef enum SectionFlags {
    IMAGE_SCN_TYPE_NO_PAD=8,
    IMAGE_SCN_RESERVED_0001=16,
    IMAGE_SCN_CNT_CODE=32,
    IMAGE_SCN_CNT_INITIALIZED_DATA=64,
    IMAGE_SCN_CNT_UNINITIALIZED_DATA=128,
    IMAGE_SCN_LNK_OTHER=256,
    IMAGE_SCN_LNK_INFO=512,
    IMAGE_SCN_RESERVED_0040=1024,
    IMAGE_SCN_LNK_REMOVE=2048,
    IMAGE_SCN_LNK_COMDAT=4096,
    IMAGE_SCN_GPREL=32768,
    IMAGE_SCN_MEM_16BIT=131072,
    IMAGE_SCN_MEM_PURGEABLE=131072,
    IMAGE_SCN_MEM_LOCKED=262144,
    IMAGE_SCN_MEM_PRELOAD=524288,
    IMAGE_SCN_ALIGN_1BYTES=1048576,
    IMAGE_SCN_ALIGN_2BYTES=2097152,
    IMAGE_SCN_ALIGN_4BYTES=3145728,
    IMAGE_SCN_ALIGN_8BYTES=4194304,
    IMAGE_SCN_ALIGN_16BYTES=5242880,
    IMAGE_SCN_ALIGN_32BYTES=6291456,
    IMAGE_SCN_ALIGN_64BYTES=7340032,
    IMAGE_SCN_ALIGN_128BYTES=8388608,
    IMAGE_SCN_ALIGN_256BYTES=9437184,
    IMAGE_SCN_ALIGN_512BYTES=10485760,
    IMAGE_SCN_ALIGN_1024BYTES=11534336,
    IMAGE_SCN_ALIGN_2048BYTES=12582912,
    IMAGE_SCN_ALIGN_4096BYTES=13631488,
    IMAGE_SCN_ALIGN_8192BYTES=14680064,
    IMAGE_SCN_LNK_NRELOC_OVFL=16777216,
    IMAGE_SCN_MEM_DISCARDABLE=33554432,
    IMAGE_SCN_MEM_NOT_CACHED=67108864,
    IMAGE_SCN_MEM_NOT_PAGED=134217728,
    IMAGE_SCN_MEM_SHARED=268435456,
    IMAGE_SCN_MEM_EXECUTE=536870912,
    IMAGE_SCN_MEM_READ=1073741824,
    IMAGE_SCN_MEM_WRITE=2147483648
} SectionFlags;

union Misc {
    dword PhysicalAddress;
    dword VirtualSize;
};

struct IMAGE_SECTION_HEADER {
    char Name[8];
    union Misc Misc;
    ImageBaseOffset32 VirtualAddress;
    dword SizeOfRawData;
    dword PointerToRawData;
    dword PointerToRelocations;
    dword PointerToLinenumbers;
    word NumberOfRelocations;
    word NumberOfLinenumbers;
    enum SectionFlags Characteristics;
};

typedef struct IMAGE_NT_HEADERS64 IMAGE_NT_HEADERS64, *PIMAGE_NT_HEADERS64;

struct IMAGE_NT_HEADERS64 {
    char Signature[4];
    struct IMAGE_FILE_HEADER FileHeader;
    struct IMAGE_OPTIONAL_HEADER64 OptionalHeader;
};

typedef struct IMAGE_BASE_RELOCATION IMAGE_BASE_RELOCATION, *PIMAGE_BASE_RELOCATION;

struct IMAGE_BASE_RELOCATION {
    dword VirtualAddress;
    dword SizeOfBlock;
};

typedef struct IMAGE_THUNK_DATA64 IMAGE_THUNK_DATA64, *PIMAGE_THUNK_DATA64;

struct IMAGE_THUNK_DATA64 {
    qword StartAddressOfRawData;
    qword EndAddressOfRawData;
    qword AddressOfIndex;
    qword AddressOfCallBacks;
    dword SizeOfZeroFill;
    dword Characteristics;
};

typedef struct IMAGE_RESOURCE_DATA_ENTRY IMAGE_RESOURCE_DATA_ENTRY, *PIMAGE_RESOURCE_DATA_ENTRY;

struct IMAGE_RESOURCE_DATA_ENTRY {
    dword OffsetToData;
    dword Size;
    dword CodePage;
    dword Reserved;
};

typedef struct IMAGE_RESOURCE_DIRECTORY IMAGE_RESOURCE_DIRECTORY, *PIMAGE_RESOURCE_DIRECTORY;

struct IMAGE_RESOURCE_DIRECTORY {
    dword Characteristics;
    dword TimeDateStamp;
    word MajorVersion;
    word MinorVersion;
    word NumberOfNamedEntries;
    word NumberOfIdEntries;
};

typedef struct _iobuf _iobuf, *P_iobuf;

struct _iobuf {
    char *_ptr;
    int _cnt;
    char *_base;
    int _flag;
    int _file;
    int _charbuf;
    int _bufsiz;
    char *_tmpfname;
};

typedef struct _iobuf FILE;

typedef int PMFN;

typedef struct _s_ThrowInfo _s_ThrowInfo, *P_s_ThrowInfo;

struct _s_ThrowInfo {
    uint attributes;
    PMFN pmfnUnwind;
    int pForwardCompat;
    int pCatchableTypeArray;
};

typedef struct TypeDescriptor TypeDescriptor, *PTypeDescriptor;

struct TypeDescriptor {
    void *pVFTable;
    void *spare;
    char name[0];
};

typedef struct _s_ThrowInfo ThrowInfo;

typedef char *va_list;

typedef ulonglong uintptr_t;

typedef struct HIMC__ HIMC__, *PHIMC__;

struct HIMC__ {
    int unused;
};

typedef struct tagCOMPOSITIONFORM tagCOMPOSITIONFORM, *PtagCOMPOSITIONFORM;

struct tagCOMPOSITIONFORM {
    DWORD dwStyle;
    POINT ptCurrentPos;
    RECT rcArea;
};

typedef struct tagCOMPOSITIONFORM *LPCOMPOSITIONFORM;

typedef struct HIMC__ *HIMC;

typedef struct tagCANDIDATEFORM tagCANDIDATEFORM, *PtagCANDIDATEFORM;

struct tagCANDIDATEFORM {
    DWORD dwIndex;
    DWORD dwStyle;
    POINT ptCurrentPos;
    RECT rcArea;
};

typedef struct tagCANDIDATEFORM *LPCANDIDATEFORM;

typedef struct _Mbstatet _Mbstatet, *P_Mbstatet;

struct _Mbstatet { // PlaceHolder Structure
};

typedef struct basic_ostream<wchar_t,struct_std::char_traits<wchar_t>_> basic_ostream<wchar_t,struct_std::char_traits<wchar_t>_>, *Pbasic_ostream<wchar_t,struct_std::char_traits<wchar_t>_>;

struct basic_ostream<wchar_t,struct_std::char_traits<wchar_t>_> { // PlaceHolder Structure
};

typedef struct basic_streambuf<wchar_t,std::char_traits<wchar_t>_> basic_streambuf<wchar_t,std::char_traits<wchar_t>_>, *Pbasic_streambuf<wchar_t,std::char_traits<wchar_t>_>;

struct basic_streambuf<wchar_t,std::char_traits<wchar_t>_> { // PlaceHolder Structure
};

typedef struct basic_istream<char,struct_std::char_traits<char>_> basic_istream<char,struct_std::char_traits<char>_>, *Pbasic_istream<char,struct_std::char_traits<char>_>;

struct basic_istream<char,struct_std::char_traits<char>_> { // PlaceHolder Structure
};

typedef struct codecvt_base codecvt_base, *Pcodecvt_base;

struct codecvt_base { // PlaceHolder Structure
};

typedef struct basic_ostream<wchar_t,std::char_traits<wchar_t>_> basic_ostream<wchar_t,std::char_traits<wchar_t>_>, *Pbasic_ostream<wchar_t,std::char_traits<wchar_t>_>;

struct basic_ostream<wchar_t,std::char_traits<wchar_t>_> { // PlaceHolder Structure
};

typedef struct basic_streambuf<wchar_t,struct_std::char_traits<wchar_t>_> basic_streambuf<wchar_t,struct_std::char_traits<wchar_t>_>, *Pbasic_streambuf<wchar_t,struct_std::char_traits<wchar_t>_>;

struct basic_streambuf<wchar_t,struct_std::char_traits<wchar_t>_> { // PlaceHolder Structure
};

typedef struct locale locale, *Plocale;

struct locale { // PlaceHolder Structure
};

typedef struct basic_istream<char,std::char_traits<char>_> basic_istream<char,std::char_traits<char>_>, *Pbasic_istream<char,std::char_traits<char>_>;

struct basic_istream<char,std::char_traits<char>_> { // PlaceHolder Structure
};

typedef struct _Fac_tidy_reg_t _Fac_tidy_reg_t, *P_Fac_tidy_reg_t;

struct _Fac_tidy_reg_t { // PlaceHolder Structure
};

typedef struct basic_streambuf<char,std::char_traits<char>_> basic_streambuf<char,std::char_traits<char>_>, *Pbasic_streambuf<char,std::char_traits<char>_>;

struct basic_streambuf<char,std::char_traits<char>_> { // PlaceHolder Structure
};

typedef struct basic_streambuf<char,struct_std::char_traits<char>_> basic_streambuf<char,struct_std::char_traits<char>_>, *Pbasic_streambuf<char,struct_std::char_traits<char>_>;

struct basic_streambuf<char,struct_std::char_traits<char>_> { // PlaceHolder Structure
};

typedef struct basic_iostream<char,std::char_traits<char>_> basic_iostream<char,std::char_traits<char>_>, *Pbasic_iostream<char,std::char_traits<char>_>;

struct basic_iostream<char,std::char_traits<char>_> { // PlaceHolder Structure
};

typedef struct ios_base ios_base, *Pios_base;

struct ios_base { // PlaceHolder Structure
};

typedef struct basic_ios<char,std::char_traits<char>_> basic_ios<char,std::char_traits<char>_>, *Pbasic_ios<char,std::char_traits<char>_>;

struct basic_ios<char,std::char_traits<char>_> { // PlaceHolder Structure
};

typedef struct _Smanip<__int64> _Smanip<__int64>, *P_Smanip<__int64>;

struct _Smanip<__int64> { // PlaceHolder Structure
};

typedef struct _Facet_base _Facet_base, *P_Facet_base;

struct _Facet_base { // PlaceHolder Structure
};

typedef struct basic_iostream<wchar_t,std::char_traits<wchar_t>_> basic_iostream<wchar_t,std::char_traits<wchar_t>_>, *Pbasic_iostream<wchar_t,std::char_traits<wchar_t>_>;

struct basic_iostream<wchar_t,std::char_traits<wchar_t>_> { // PlaceHolder Structure
};

typedef struct basic_ostream<char,struct_std::char_traits<char>_> basic_ostream<char,struct_std::char_traits<char>_>, *Pbasic_ostream<char,struct_std::char_traits<char>_>;

struct basic_ostream<char,struct_std::char_traits<char>_> { // PlaceHolder Structure
};

typedef struct basic_iostream<char,struct_std::char_traits<char>_> basic_iostream<char,struct_std::char_traits<char>_>, *Pbasic_iostream<char,struct_std::char_traits<char>_>;

struct basic_iostream<char,struct_std::char_traits<char>_> { // PlaceHolder Structure
};

typedef struct function<void___cdecl(void)> function<void___cdecl(void)>, *Pfunction<void___cdecl(void)>;

struct function<void___cdecl(void)> { // PlaceHolder Structure
};

typedef struct basic_ostream<char,std::char_traits<char>_> basic_ostream<char,std::char_traits<char>_>, *Pbasic_ostream<char,std::char_traits<char>_>;

struct basic_ostream<char,std::char_traits<char>_> { // PlaceHolder Structure
};

typedef struct codecvt<char,char,_Mbstatet> codecvt<char,char,_Mbstatet>, *Pcodecvt<char,char,_Mbstatet>;

struct codecvt<char,char,_Mbstatet> { // PlaceHolder Structure
};

typedef struct basic_ios<wchar_t,std::char_traits<wchar_t>_> basic_ios<wchar_t,std::char_traits<wchar_t>_>, *Pbasic_ios<wchar_t,std::char_traits<wchar_t>_>;

struct basic_ios<wchar_t,std::char_traits<wchar_t>_> { // PlaceHolder Structure
};

typedef struct _Lockit _Lockit, *P_Lockit;

struct _Lockit { // PlaceHolder Structure
};

typedef struct _Locimp _Locimp, *P_Locimp;

struct _Locimp { // PlaceHolder Structure
};

typedef struct facet facet, *Pfacet;

struct facet { // PlaceHolder Structure
};

typedef struct id id, *Pid;

struct id { // PlaceHolder Structure
};

typedef struct task_continuation_context task_continuation_context, *Ptask_continuation_context;

struct task_continuation_context { // PlaceHolder Structure
};

typedef struct _ContextCallback _ContextCallback, *P_ContextCallback;

struct _ContextCallback { // PlaceHolder Structure
};

typedef struct _TaskEventLogger _TaskEventLogger, *P_TaskEventLogger;

struct _TaskEventLogger { // PlaceHolder Structure
};

typedef struct _ExceptionHolder _ExceptionHolder, *P_ExceptionHolder;

struct _ExceptionHolder { // PlaceHolder Structure
};

typedef struct _Threadpool_chore _Threadpool_chore, *P_Threadpool_chore;

struct _Threadpool_chore { // PlaceHolder Structure
};

typedef int (*_onexit_t)(void);

typedef ulonglong size_t;

typedef longlong __time64_t;

typedef int errno_t;




void FUN_140001000(void);
void FUN_140001060(void);
void FUN_140001090(void);
void FUN_1400010d0(void);
void FUN_140001100(void);
void FUN_140001130(void);
void FUN_1400011c0(void);
void FUN_1400011f0(void);
float * FUN_1400014c0(float *param_1,float param_2,float param_3,float param_4,float param_5);
undefined * FUN_140001600(void);
void FUN_140001610(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
undefined8 FUN_140001670(undefined8 param_1,undefined8 param_2);
undefined8 * FUN_140001680(undefined8 *param_1,longlong param_2);
char * FUN_1400016e0(longlong param_1);
undefined8 * FUN_140001700(undefined8 *param_1,ulonglong param_2);
undefined8 * FUN_140001750(undefined8 *param_1);
void __cdecl __ExceptionPtrDestroy(void *param_1);
void * FUN_140001790(void *param_1,void *param_2);
undefined8 * FUN_1400017b0(undefined8 *param_1);
void FUN_1400017e0(void *param_1);
void FUN_1400017f0(void);
undefined8 * FUN_140001810(undefined8 *param_1,longlong param_2);
undefined8 * FUN_140001850(undefined8 *param_1,longlong param_2);
void FUN_140001890(void);
undefined8 * FUN_1400018b0(undefined8 *param_1);
undefined8 * FUN_140001920(undefined8 *param_1,longlong param_2);
undefined4 * FUN_140001960(undefined8 param_1,undefined4 *param_2,undefined4 param_3);
undefined8 FUN_140001970(longlong *param_1,undefined4 param_2,int *param_3);
longlong FUN_1400019b0(longlong param_1,int *param_2,int param_3);
undefined4 * FUN_1400019d0(undefined4 *param_1,undefined4 param_2);
longlong * FUN_1400019f0(longlong *param_1,undefined4 *param_2,longlong *param_3);
undefined8 * FUN_140001b50(undefined8 *param_1,ulonglong param_2);
longlong * FUN_140001ba0(longlong *param_1,longlong *param_2);
void FUN_140001d30(undefined4 param_1);
undefined8 * FUN_140001d70(undefined8 *param_1,longlong param_2);
undefined8 * FUN_140001dd0(undefined8 *param_1,longlong param_2);
char * FUN_140001e30(void);
undefined8 * FUN_140001e40(undefined8 param_1,undefined8 *param_2,int param_3);
void * FUN_140001e90(void *param_1,ulonglong param_2);
char * FUN_140001ec0(void);
undefined8 * FUN_140001ed0(undefined8 param_1,undefined8 *param_2,DWORD param_3);
int * FUN_140001f60(undefined8 param_1,int *param_2,int param_3);
undefined8 * FUN_140001fe0(undefined8 *param_1);
void FUN_140002010(void);
undefined8 * FUN_140002030(undefined8 *param_1,longlong param_2);
undefined8 FUN_140002070(void);
void FUN_140002080(longlong param_1);
void FUN_1400020d0(char *param_1);
undefined8 * FUN_140002160(undefined8 *param_1,ulonglong param_2);
undefined4 * FUN_140002260(undefined4 *param_1,undefined4 param_2);
void FUN_140002280(undefined4 param_1);
LPWSTR FUN_1400022c0(LPWSTR param_1,UINT param_2,undefined8 *param_3);
uint * FUN_140002410(uint *param_1,uint *param_2);
ulonglong FUN_140002500(longlong param_1);
undefined8 * FUN_140002540(undefined8 *param_1,undefined8 *param_2);
uint * FUN_140002580(uint *param_1,uint *param_2,longlong param_3);
undefined8 * FUN_1400027b0(undefined8 *param_1);
longlong * FUN_1400027c0(undefined8 *param_1,longlong *param_2);
uint * FUN_140002810(uint *param_1,undefined8 *param_2,uint *param_3);
void FUN_140002860(longlong *param_1);
undefined8 * FUN_1400028d0(undefined8 *param_1);
undefined8 * FUN_1400028f0(undefined8 *param_1,undefined8 *param_2,undefined8 *param_3);
undefined8 *FUN_140002a60(undefined8 *param_1,undefined8 *param_2,undefined8 *param_3,undefined8 *param_4);
undefined8 *FUN_140002c50(undefined8 *param_1,undefined8 *param_2,undefined8 *param_3,undefined8 *param_4,undefined8 *param_5);
longlong * FUN_140002de0(longlong param_1);
longlong *FUN_140002df0(longlong *param_1,undefined8 *param_2,undefined8 *param_3,undefined8 *param_4);
undefined8 * FUN_140003060(undefined8 *param_1,uint param_2);
void FUN_1400031b0(undefined8 *param_1);
void FUN_1400032e0(void *param_1,undefined4 param_2);
undefined8 * FUN_140003340(undefined8 *param_1,longlong param_2);
void FUN_1400033d0(void *param_1,undefined4 param_2,undefined8 *param_3);
void FUN_140003440(void *param_1,undefined8 *param_2,undefined8 *param_3);
void FUN_1400034a0(undefined8 param_1,undefined8 *param_2,undefined8 *param_3,undefined8 *param_4);
int * FUN_140003510(longlong param_1,int *param_2,uint param_3);
DWORD FUN_140003670(undefined8 *param_1);
LPCWSTR FUN_140003750(LPCWSTR param_1,undefined8 *param_2,uint param_3);
void FUN_1400038f0(undefined8 *param_1,uint *param_2);
undefined8 * FUN_140003ad0(undefined8 *param_1,undefined8 *param_2);
undefined8 * FUN_140003b20(undefined8 *param_1);
undefined8 * FUN_140003b50(undefined8 *param_1,undefined8 *param_2);
void FUN_140003b80(longlong param_1);
undefined8 * FUN_140003bd0(undefined8 *param_1,longlong param_2);
ulonglong FUN_140003c50(LPCWSTR param_1,LPCWSTR param_2);
ulonglong FUN_140003df0(LPCWSTR param_1,LPCWSTR param_2);
ulonglong FUN_140003f90(LPCWSTR param_1);
undefined8 FUN_140004020(LPCWSTR param_1);
void FUN_140004100(undefined8 *param_1);
void FUN_140004110(LPCWSTR param_1);
int * FUN_140004150(int *param_1,LPCWSTR param_2,uint param_3);
void FUN_140004230(LPCWSTR param_1);
ulonglong FUN_140004270(uint *param_1,undefined8 *param_2);
void FUN_1400044d0(uint *param_1);
undefined4 FUN_140004540(LPWSTR param_1,undefined8 param_2,undefined8 param_3);
LPWSTR FUN_140004690(LPWSTR param_1,undefined8 param_2,undefined8 param_3);
void FUN_1400046f0(LPCWSTR param_1);
void FUN_140004730(longlong param_1,LPCWSTR param_2,undefined8 param_3,longlong *param_4);
void FUN_140004f20(undefined8 *param_1,LPCWSTR param_2);
void FUN_1400050d0(void);
undefined8 * FUN_1400050f0(undefined8 *param_1);
void FUN_140005160(_Threadpool_chore *param_1);
void FUN_1400051c0(undefined8 param_1,undefined8 param_2,undefined8 param_3);
_Threadpool_chore * FUN_140005250(_Threadpool_chore *param_1);
undefined * FUN_140005280(void);
void FUN_140005350(undefined8 *param_1);
undefined8 * FUN_140005370(undefined8 *param_1,ulonglong param_2);
undefined8 * FUN_1400053a0(undefined8 *param_1,ulonglong param_2);
void FUN_140005400(longlong param_1,longlong *param_2);
void FUN_140005530(longlong param_1,longlong *param_2);
void FUN_140005690(longlong *param_1);
void FUN_1400056d0(longlong *param_1);
undefined8 * FUN_140005710(undefined8 *param_1,ulonglong param_2);
void FUN_140005740(void);
undefined8 * FUN_140005760(undefined8 *param_1,longlong param_2);
void ~pair<>(longlong param_1);
void FUN_140005800(longlong *param_1);
void FUN_140005860(undefined8 *param_1);
void FUN_1400058b0(longlong *param_1);
void FUN_1400058e0(_ContextCallback *param_1);
void FUN_1400058f0(_ExceptionHolder *param_1);
void FUN_140005970(undefined4 *param_1);
undefined8 * FUN_1400059a0(undefined8 *param_1,undefined8 *param_2);
task_continuation_context * FUN_140005a40(task_continuation_context *param_1);
void FUN_140005a90(_ContextCallback *param_1);
void FUN_140005aa0(undefined8 *param_1);
undefined8 * FUN_140005ac0(undefined8 *param_1,longlong param_2,undefined8 *param_3);
void FUN_140005c60(undefined8 *param_1);
ulonglong FUN_140005d50(longlong param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
undefined1 FUN_140005eb0(longlong *param_1,void *param_2);
bool FUN_140006000(longlong param_1);
void FUN_140006010(longlong param_1,undefined **param_2,int param_3);
void FUN_140006090(longlong param_1,undefined **param_2);
void FUN_140006270(longlong *param_1);
void FUN_140006440(longlong param_1);
undefined8 * FUN_140006580(undefined8 *param_1,uint param_2);
void FUN_1400065c0(longlong param_1);
void FUN_140006650(longlong param_1);
longlong FUN_1400066a0(longlong param_1,longlong *param_2);
void FUN_140006790(longlong param_1);
undefined8 * FUN_140006870(undefined8 *param_1,undefined4 param_2);
char * __thiscall std::future_error::what(future_error *this);
void FUN_140006940(undefined4 param_1);
undefined8 * FUN_140006970(undefined8 *param_1,longlong param_2);
undefined8 * FUN_1400069c0(undefined8 *param_1,longlong param_2);
char * FUN_140006a00(void);
undefined8 * FUN_140006a10(undefined8 param_1,undefined8 *param_2,int param_3);
undefined8 * FUN_140006ac0(undefined8 *param_1,void *param_2);
void FUN_140006b00(undefined8 *param_1,void *param_2,size_t param_3);
uint * FUN_140006c40(uint *param_1,uint *param_2,uint *param_3,undefined8 param_4,undefined8 param_5,int *param_6);
uint * FUN_1400071d0(uint *param_1,uint *param_2,uint *param_3,undefined8 param_4);
void FUN_140007430(longlong param_1);
bool FUN_1400074a0(longlong param_1,void *param_2,int param_3);
int FUN_140007570(longlong param_1);
uint FUN_140007630(longlong param_1);
void * FUN_1400076f0(void *param_1,int param_2,int param_3,uint param_4,uint param_5);
void * FUN_140007b80(void *param_1,int param_2,undefined8 param_3,int param_4,int param_5);
void * FUN_140007fe0(float *param_1,int param_2,uint param_3,uint param_4);
undefined8 FUN_140008210(void *param_1,uint *param_2);
void FUN_1400083c0(longlong *param_1);
undefined8 FUN_140008540(longlong *param_1,short *param_2,longlong param_3,longlong param_4,longlong param_5,int param_6,short *param_7);
undefined8 FUN_140008970(longlong *param_1,short *param_2,longlong param_3,int param_4);
undefined8 FUN_140008bf0(longlong *param_1,longlong param_2,longlong param_3,longlong param_4);
void FUN_1400091e0(longlong param_1,int param_2,longlong param_3);
void FUN_140009800(char *param_1,int param_2,short *param_3);
ulonglong FUN_14000a030(longlong *param_1);
undefined8 FUN_14000a100(longlong *param_1);
void FUN_14000a8d0(longlong *param_1);
bool FUN_14000aab0(longlong *param_1,int param_2);
undefined8 FUN_14000b050(longlong *param_1);
undefined4 FUN_14000b3d0(longlong param_1,uint param_2,undefined4 param_3);
undefined4 FUN_14000b460(undefined8 *param_1,int param_2);
bool FUN_14000ba30(longlong *param_1,int param_2);
undefined8 FUN_14000bc20(longlong *param_1);
ulonglong FUN_14000be50(ulonglong param_1,ulonglong param_2,ulonglong param_3,uint param_4);
byte * FUN_14000c060(byte *param_1,byte *param_2,undefined8 param_3,int param_4);
undefined1 * FUN_14000c150(undefined1 *param_1,byte *param_2,byte *param_3,int param_4);
char * FUN_14000c210(char *param_1,byte *param_2,ulonglong *param_3,int param_4);
void FUN_14000c450(longlong param_1,longlong param_2,longlong param_3,byte *param_4,int param_5,int param_6);
void FUN_14000c580(undefined1 (*param_1) [16],longlong param_2,longlong param_3,longlong param_4,int param_5,int param_6);
undefined * FUN_14000c820(longlong param_1);
void * FUN_14000c8a0(longlong *param_1,undefined4 *param_2,undefined4 *param_3);
undefined8 FUN_14000cd30(void *param_1,byte *param_2,uint param_3);
uint FUN_14000cfb0(longlong param_1,longlong param_2);
undefined8 FUN_14000d0a0(longlong param_1,undefined8 param_2,int param_3);
undefined8 FUN_14000d160(undefined8 *param_1);
bool FUN_14000d4c0(undefined8 *param_1);
undefined8 FUN_14000d970(longlong *param_1);
undefined8 FUN_14000db00(longlong *param_1,int param_2);
undefined8 FUN_14000ddf0(longlong param_1);
undefined8 FUN_14000dea0(undefined8 *param_1,byte *param_2,uint param_3,uint param_4,uint param_5,uint param_6,uint param_7,int param_8);
undefined8 FUN_14000f040(undefined8 *param_1,byte *param_2,uint param_3,uint param_4,uint param_5,int param_6,int param_7);
undefined8 FUN_14000f3e0(undefined8 *param_1);
int FUN_140010040(uint param_1);
undefined4 FUN_1400100b0(uint *param_1,uint *param_2);
void * FUN_140010530(uint *param_1,uint *param_2,uint *param_3);
undefined8 FUN_140011300(longlong param_1);
undefined1 * FUN_1400115c0(longlong param_1,uint *param_2,uint *param_3);
undefined8 FUN_140011fe0(longlong param_1,byte *param_2,uint param_3);
undefined2 *FUN_140012180(longlong param_1,int *param_2,int *param_3,undefined8 param_4,undefined8 param_5,int *param_6);
undefined8 FUN_140012d00(longlong param_1,longlong param_2);
longlong FUN_140012da0(longlong param_1,uint param_2,longlong param_3);
longlong FUN_140012ea0(longlong param_1,uint param_2,int param_3,undefined8 param_4,longlong param_5);
void * FUN_140013470(longlong param_1,uint *param_2,uint *param_3,undefined8 param_4);
longlong FUN_140013660(longlong param_1);
undefined8 FUN_140013780(longlong param_1);
void FUN_1400138f0(longlong param_1,longlong param_2,int param_3,int param_4);
undefined8 FUN_140013a40(longlong param_1,uint *param_2);
void FUN_140013d20(longlong param_1,ushort param_2);
undefined8 FUN_140013e30(longlong param_1,longlong param_2);
void FUN_140014290(int *param_1,int param_2,int param_3,int param_4,int param_5);
longlong FUN_140014310(longlong param_1,uint *param_2);
undefined8 FUN_1400149d0(longlong param_1);
longlong FUN_140014af0(longlong param_1,longlong param_2);
void FUN_140014ca0(float *param_1,byte *param_2,int param_3);
float * FUN_140014dd0(longlong param_1,uint *param_2,long *param_3);
void * FUN_140015560(uint *param_1,uint *param_2,uint *param_3);
void FUN_1400156d0(longlong param_1,char *param_2);
int FUN_140015890(longlong param_1,char *param_2);
undefined8 FUN_1400159a0(longlong param_1,int *param_2,int *param_3,undefined4 *param_4);
int FUN_140015dd0(int param_1,float param_2);
void FUN_140015e50(int param_1,undefined8 param_2,int param_3,int param_4,float param_5,int *param_6,float *param_7);
void FUN_140016110(longlong param_1,longlong param_2,int param_3,float param_4,int param_5,uint param_6);
void FUN_140016600(int *param_1,longlong param_2,uint param_3,float param_4,float param_5,int param_6,uint param_7);
void FUN_140016a00(longlong *param_1,int param_2);
void FUN_1400180c0(longlong param_1,longlong param_2);
void FUN_140018870(longlong param_1,longlong param_2);
void FUN_140019040(longlong *param_1,int param_2);
void FUN_140019140(longlong param_1,uint param_2,longlong param_3,longlong param_4,int param_5,int param_6,uint param_7);
void FUN_140019e90(longlong param_1,int param_2);
void FUN_14001a630(longlong param_1,int param_2);
void FUN_14001ac30(longlong *param_1);
void FUN_14001ae10(longlong param_1,int param_2);
void FUN_14001af30(longlong *param_1);
int FUN_14001b1e0(longlong param_1);
undefined8 FUN_14001b400(longlong *param_1,longlong param_2,undefined8 param_3,longlong param_4);
ulonglong FUN_14001b7b0(undefined8 param_1,longlong param_2,undefined8 param_3,int param_4,undefined8 param_5,longlong param_6,int param_7,int param_8,undefined8 param_9,float param_10,float param_11,float param_12,float param_13);
void FUN_14001b960(undefined8 *param_1);
void FUN_14001b970(longlong *param_1,longlong *param_2,undefined8 *param_3);
ulonglong FUN_14001bb00(void);
void FUN_14001bb50(undefined4 param_1,undefined8 param_2,undefined8 param_3);
void FUN_14001be00(longlong param_1);
void FUN_14001be70(undefined4 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
void FUN_14001bea0(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
void FUN_14001bed0(void);
longlong * FUN_14001bf30(longlong *param_1,longlong *param_2,undefined ***param_3);
void FUN_14001cd10(longlong *param_1);
void FUN_14001cdd0(longlong *param_1);
uint * FUN_14001ce50(uint *param_1,char *param_2,uint param_3,undefined8 param_4);
void FUN_14001d7b0(longlong param_1);
void FUN_14001d810(undefined8 *param_1);
void FUN_14001d820(uint *param_1,float param_2);
HANDLE FUN_14001d8f0(DWORD *param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
ulonglong *****FUN_14001db10(DWORD *param_1,ulonglong *param_2,undefined8 param_3,undefined8 param_4);
undefined4 FUN_14001deb0(undefined8 *param_1);
longlong * FUN_14001dfc0(longlong *param_1,wchar_t *param_2);
void FUN_14001f440(longlong *param_1);
longlong * FUN_14001f4b0(longlong *param_1);
void FUN_14001ffd0(longlong *param_1);
void FUN_140020040(void *param_1);
ulonglong * FUN_140020050(ulonglong *param_1,__uint64 param_2);
void FUN_1400202e0(longlong *param_1);
ulonglong * FUN_140020360(ulonglong *param_1,int param_2);
void FUN_1400205e0(longlong *param_1);
void FUN_140020660(void *param_1);
ulonglong ***** FUN_140020670(uint param_1,ulonglong *param_2,undefined8 param_3,undefined8 param_4);
void FUN_140021e70(longlong *param_1);
ulonglong FUN_140021ea0(DWORD param_1,undefined8 param_2,longlong param_3,undefined8 param_4);
ulonglong *FUN_140021f60(ulonglong *param_1,ulonglong param_2,SIZE_T param_3,longlong param_4,longlong param_5,longlong *param_6);
undefined8 FUN_140022ff0(DWORD param_1,undefined4 *param_2,undefined8 param_3,longlong param_4,int param_5);
undefined4 * FUN_140028d20(undefined4 *param_1);
void FUN_140028d50(longlong *param_1,undefined8 *param_2);
longlong * FUN_140028db0(longlong *param_1,longlong *param_2,int *param_3);
ulonglong * FUN_1400293e0(ulonglong *param_1,longlong *param_2);
void FUN_140029430(longlong *param_1);
undefined8 * FUN_140029490(undefined8 *param_1,undefined8 *param_2);
void FUN_1400294c0(longlong param_1);
undefined8 FUN_140029510(HINSTANCE param_1,undefined8 param_2,undefined8 param_3,uint param_4);
LRESULT FUN_14002aaa0(HWND param_1,uint param_2,ulonglong param_3,ulonglong param_4);
void FUN_14002ab50(longlong *param_1);
void FUN_14002abb0(longlong *param_1);
void FUN_14002ac30(longlong *param_1,undefined8 *param_2);
void thunk_FUN_14002ebd0(longlong *param_1);
void FUN_14002ac90(longlong *param_1,undefined4 *param_2);
void FUN_14002acb0(longlong *param_1);
longlong * FUN_14002ad10(longlong *param_1);
ulonglong * FUN_14002ad80(longlong param_1,ulonglong *param_2,longlong *param_3,byte param_4);
ulonglong *FUN_14002ae90(longlong param_1,ulonglong *param_2,longlong param_3,int param_4,byte param_5);
undefined2 FUN_14002b010(longlong param_1);
short FUN_14002b090(longlong param_1,short param_2);
wchar_t FUN_14002b0f0(basic_streambuf<> *param_1,wchar_t param_2);
void FUN_14002b340(basic_streambuf<> *param_1);
longlong * FUN_14002b410(longlong param_1,longlong *param_2);
basic_iostream<> * FUN_14002b500(basic_iostream<> *param_1);
ulonglong FUN_14002b5c0(undefined8 param_1,undefined8 *param_2);
void FID_conflict:~vector<>(longlong *param_1);
void FID_conflict:~vector<>(longlong *param_1);
basic_iostream<> * FUN_14002b6f0(basic_iostream<> *param_1,basic_iostream<> *param_2);
basic_iostream<> * FUN_14002b7e0(basic_iostream<> *param_1,undefined8 *param_2);
void FUN_14002b8b0(longlong *param_1);
basic_ostream<> * FUN_14002b8f0(basic_ostream<> *param_1,char *param_2);
void FUN_14002ba00(longlong *param_1);
void FUN_14002ba70(longlong param_1);
longlong * FUN_14002baf0(longlong *param_1,longlong *param_2);
void FUN_14002bb20(longlong *param_1);
ulonglong * FUN_14002bb90(ulonglong *param_1,longlong *param_2);
ulonglong * FUN_14002bc50(ulonglong *param_1,longlong *param_2);
void FUN_14002bd10(basic_streambuf<> *param_1,locale *param_2);
int FUN_14002bd60(longlong *param_1);
basic_streambuf<> * FUN_14002bdb0(basic_streambuf<> *param_1,char *param_2,size_t param_3);
longlong * FUN_14002beb0(longlong *param_1,longlong *param_2,longlong *param_3);
fpos_t * FUN_14002bf90(longlong *param_1,fpos_t *param_2,longlong param_3,int param_4);
longlong FUN_14002c0a0(basic_streambuf<> *param_1,char *param_2,size_t param_3);
longlong FUN_14002c170(basic_streambuf<> *param_1,char *param_2,ulonglong param_3);
uint FUN_14002c2c0(longlong param_1);
ulonglong FUN_14002c580(longlong *param_1);
uint FUN_14002c5f0(longlong param_1,uint param_2);
int FUN_14002c6d0(basic_streambuf<> *param_1,int param_2);
void FUN_14002c880(longlong param_1);
void FUN_14002c8a0(longlong param_1);
void FUN_14002c8c0(basic_streambuf<> *param_1);
longlong FUN_14002c930(longlong *param_1,longlong *param_2);
longlong * FUN_14002c950(longlong *param_1,longlong *param_2);
longlong * FUN_14002ca10(longlong *param_1,longlong *param_2,undefined8 param_3,undefined8 param_4);
longlong * FUN_14002cae0(longlong *param_1);
void FUN_14002cb20(undefined8 *param_1);
void FUN_14002cbe0(longlong *param_1,longlong *param_2);
longlong FUN_14002cc30(longlong *param_1);
undefined8 * FUN_14002cc60(longlong param_1,undefined8 *param_2,void *param_3);
void FUN_14002ccb0(longlong *param_1,undefined8 *param_2);
void FUN_14002ccf0(longlong *param_1);
undefined8 * FUN_14002cd70(undefined8 *param_1,undefined8 *param_2);
undefined8 FUN_14002cda0(longlong param_1,undefined8 param_2);
void FUN_14002cdd0(longlong *param_1);
ulonglong * FUN_14002ce30(ulonglong *param_1,longlong *param_2);
ulonglong FUN_14002ceb0(longlong param_1,char param_2,char param_3,undefined8 param_4,undefined8 *param_5);
void FUN_14002d1a0(longlong *param_1,longlong param_2,undefined8 *param_3);
void FUN_14002d490(longlong param_1);
void FUN_14002d5a0(undefined8 *param_1);
ulonglong * FUN_14002d5d0(longlong param_1,ulonglong *param_2,longlong *param_3,byte param_4);
ulonglong *FUN_14002d6d0(longlong param_1,ulonglong *param_2,longlong param_3,int param_4,byte param_5);
ulonglong FUN_14002d840(longlong param_1);
int FUN_14002d8c0(longlong param_1,int param_2);
int FUN_14002d920(basic_streambuf<> *param_1,int param_2);
undefined4 FUN_14002db40(undefined4 *param_1);
void FUN_14002db50(longlong *param_1);
undefined8 * FUN_14002dbb0(undefined8 *param_1,undefined8 *param_2);
undefined8 *FUN_14002dcd0(undefined8 *param_1,undefined8 *param_2,ulonglong param_3,ulonglong param_4);
longlong FUN_14002dd30(short *param_1,short param_2);
longlong FUN_14002dd90(short *param_1);
longlong * FUN_14002dde0(undefined8 *param_1,longlong *param_2);
undefined8 * FUN_14002de00(undefined8 *param_1,undefined8 *param_2);
undefined8 * FUN_14002de20(undefined8 *param_1,void *param_2,ulonglong param_3);
void FUN_14002dea0(undefined8 *param_1,undefined8 *param_2);
longlong * FUN_14002dec0(longlong *param_1,longlong *param_2,undefined8 param_3);
longlong * FUN_14002df40(longlong *param_1,longlong *param_2);
undefined8 * FUN_14002dfe0(undefined8 *param_1,void *param_2);
undefined8 * FUN_14002e020(undefined8 *param_1,undefined8 *param_2);
undefined8 * FUN_14002e150(undefined8 *param_1);
longlong * FUN_14002e160(longlong *param_1,void *param_2,size_t param_3);
void FUN_14002e1e0(longlong *param_1,void *param_2);
longlong * FUN_14002e200(longlong *param_1,longlong *param_2);
undefined8 * FUN_14002e290(undefined8 *param_1,undefined8 *param_2);
undefined8 * FUN_14002e3b0(undefined8 *param_1);
basic_streambuf<> * FUN_14002e3d0(basic_streambuf<> *param_1,uint param_2);
basic_ios<> * FUN_14002e410(basic_ios<> *param_1,uint param_2);
basic_ios<> * FUN_14002e4b0(basic_ios<> *param_1,uint param_2);
basic_ios<> * FUN_14002e570(basic_ios<> *param_1,uint param_2);
basic_ios<> * FUN_14002e610(basic_ios<> *param_1,uint param_2);
basic_ios<> * FUN_14002e6b0(basic_ios<> *param_1,uint param_2);
basic_streambuf<> * FUN_14002e770(basic_streambuf<> *param_1,uint param_2);
longlong * FUN_14002e800(longlong param_1,uint param_2);
undefined8 * FUN_14002e840(undefined8 *param_1,uint param_2);
undefined8 * FUN_14002e8f0(undefined8 *param_1,ulonglong param_2);
basic_streambuf<> * FUN_14002e970(basic_streambuf<> *param_1,uint param_2);
basic_ios<> * FUN_14002e9c0(basic_ios<> *param_1,uint param_2);
void FUN_14002ea80(longlong *param_1);
void FUN_14002eac0(longlong *param_1);
void FUN_14002eb00(longlong *param_1);
void FUN_14002ebd0(longlong *param_1);
basic_ostream<> * FUN_14002ec40(basic_ostream<> *param_1,wchar_t *param_2);
bool FUN_14002ed50(longlong *param_1);
basic_streambuf<> * FUN_14002ee40(basic_streambuf<> *param_1);
basic_streambuf<> * FUN_14002eef0(basic_streambuf<> *param_1,char *param_2,int param_3);
undefined8 FUN_14002f030(undefined8 param_1);
void FUN_14002f040(longlong param_1);
void FUN_14002f0e0(longlong param_1,undefined1 param_2);
undefined8 * FUN_14002f1a0(undefined8 *param_1,undefined8 *param_2);
void FUN_14002f220(longlong param_1);
void FUN_14002f2d0(undefined8 *param_1,ulonglong param_2);
longlong * FUN_14002f360(longlong *param_1,void *param_2,size_t param_3);
void FUN_14002f4c0(longlong param_1,undefined8 *param_2,char param_3);
void _guard_check_icall(void);
undefined1 FUN_14002f520(void);
longlong * FUN_14002f530(longlong *param_1,char param_2);
void FUN_14002f670(longlong *param_1);
void FUN_14002f730(undefined8 *param_1);
void FUN_14002f7e0(longlong *param_1);
void FUN_14002f810(longlong *param_1,longlong *param_2);
void FUN_14002f880(undefined8 param_1,void *param_2,longlong param_3);
basic_streambuf<> * FUN_14002f8d0(basic_streambuf<> *param_1,wchar_t *param_2,int param_3);
void FUN_14002fa10(longlong param_1,undefined8 *param_2,uint param_3);
void FUN_14002fb10(longlong param_1,void *param_2,ulonglong param_3,uint param_4);
void FUN_14002fc50(void);
undefined8 * FUN_14002fc70(undefined8 *param_1,uint param_2);
_Facet_base * FUN_14002fcb0(locale *param_1);
longlong * FUN_14002fdc0(longlong *param_1,longlong *param_2);
longlong * FUN_14002fe20(longlong *param_1,longlong *param_2,undefined8 *param_3);
undefined8 * FUN_14002fe90(undefined8 *param_1,undefined8 *param_2);
longlong * FUN_14002fed0(longlong *param_1,undefined8 param_2,undefined8 *param_3);
LPSTR FUN_140030020(LPSTR param_1,UINT param_2,undefined8 *param_3);
undefined4 FUN_140030100(undefined8 *param_1,undefined8 *param_2);
undefined4 FUN_140030280(undefined4 *param_1,undefined4 param_2);
undefined8 FUN_140030290(undefined8 *param_1);
basic_istream<> * FUN_1400302a0(basic_istream<> *param_1,longlong *param_2);
basic_istream<> * FUN_140030490(basic_istream<> *param_1);
ulonglong FUN_1400305c0(undefined8 *param_1,ushort *param_2);
basic_istream<> * thunk_FUN_140034c60(basic_istream<> *param_1,longlong *param_2,uint param_3);
void FUN_140030620(basic_ostream<> *param_1,char *param_2);
ulonglong * FUN_140030640(ulonglong *param_1,undefined1 *param_2,undefined1 *param_3);
basic_ostream<> * FUN_140030770(basic_ostream<> *param_1,char *param_2);
undefined2 FUN_140030940(DWORD param_1,LPCVOID param_2,undefined1 *param_3,undefined8 param_4);
undefined8 FUN_1400309e0(DWORD param_1,LPCVOID param_2,undefined1 *param_3,undefined8 param_4);
longlong FUN_140030a80(DWORD param_1,LPVOID param_2,undefined4 param_3,undefined8 param_4);
longlong FUN_140030b20(DWORD param_1,LPVOID param_2,undefined8 param_3,undefined8 param_4);
longlong FUN_140030bc0(DWORD param_1,LPVOID param_2,undefined8 param_3,undefined8 param_4);
undefined8 *FUN_140030c60(undefined8 *param_1,undefined2 *param_2,undefined2 *param_3,undefined2 *param_4,undefined *param_5);
ulonglong * FUN_140030cc0(ulonglong *param_1,undefined1 *param_2,undefined1 *param_3);
LPWSTR FUN_140030e00(LPWSTR param_1);
LPWSTR FUN_140030e40(LPWSTR param_1);
longlong * FUN_140030e80(longlong *param_1,undefined8 *param_2);
basic_ostream<> * FUN_140030eb0(basic_ostream<> *param_1);
basic_ostream<> * FUN_140031070(basic_ostream<> *param_1,wchar_t *param_2);
basic_ostream<> * FUN_1400310c0(basic_ostream<> *param_1);
LPWSTR FUN_140031100(LPWSTR param_1);
undefined8 * FUN_140031140(undefined8 *param_1,undefined8 *param_2,undefined8 *param_3);
undefined8 * FUN_1400312c0(undefined8 *param_1,undefined8 *param_2,undefined8 *param_3);
undefined8 * FUN_140031330(undefined8 *param_1,undefined8 *param_2,void *param_3);
undefined8 * FUN_1400314c0(undefined8 *param_1,undefined8 *param_2,void *param_3);
bool FUN_140031530(longlong *param_1,longlong *param_2);
LPWSTR FUN_140031630(LPWSTR param_1);
char * FUN_140031670(char *param_1,undefined8 param_2,undefined8 *param_3);
undefined8 * FUN_1400317b0(undefined8 *param_1,undefined8 param_2,undefined8 *param_3);
LPWSTR FUN_1400318e0(LPWSTR param_1,undefined8 *param_2);
undefined8 * FUN_140031940(undefined8 *param_1);
undefined8 * FUN_1400319e0(undefined8 *param_1,undefined8 *param_2);
undefined8 * FUN_140031a70(undefined8 *param_1);
undefined8 * FUN_140031b10(undefined8 *param_1,undefined8 param_2,undefined8 *param_3);
undefined8 *FUN_140031c60(undefined8 *param_1,undefined8 param_2,undefined8 *param_3,undefined4 *param_4);
void FUN_140031e40(longlong *param_1,longlong *param_2,ulonglong param_3);
void FUN_140032060(longlong *param_1,longlong *param_2,ulonglong param_3);
_Facet_base * FUN_1400322a0(locale *param_1);
undefined8 * FUN_1400323b0(longlong *param_1,undefined8 *param_2,undefined8 *param_3);
undefined8 * FUN_140032540(longlong *param_1,undefined8 *param_2,longlong *param_3);
void FUN_1400326f0(longlong *param_1,undefined8 param_2);
void FUN_140032760(undefined8 param_1,longlong *param_2,ulonglong param_3);
void FUN_1400329b0(ulonglong *param_1,void *param_2,size_t param_3);
void FUN_140032ae0(ulonglong *param_1,void *param_2,ulonglong param_3);
undefined8 * FUN_140032c50(undefined8 *param_1,ulonglong param_2);
undefined8 *FUN_140032dc0(undefined8 *param_1,undefined8 param_2,undefined8 param_3,undefined2 param_4);
undefined8 *FUN_140032f60(undefined8 *param_1,ulonglong param_2,undefined8 param_3,void *param_4,longlong param_5);
void FUN_140033130(undefined8 *param_1,void *param_2,ulonglong param_3);
undefined8 * FUN_140033250(undefined8 *param_1,ulonglong param_2);
undefined8 *FUN_1400333a0(undefined8 *param_1,ulonglong param_2,undefined8 param_3,void *param_4,size_t param_5);
ulonglong FUN_140033530(size_t param_1);
void FUN_140033590(longlong param_1,longlong param_2);
void FUN_140033610(longlong *param_1,longlong *param_2);
void FUN_1400336a0(longlong *param_1,longlong *param_2);
longlong * FUN_140033730(longlong *param_1,ulonglong param_2,undefined8 param_3,void *param_4);
undefined8 *FUN_140033890(undefined8 *param_1,ulonglong param_2,undefined8 param_3,longlong param_4);
undefined8 *FUN_140033a50(undefined8 *param_1,undefined8 param_2,undefined8 param_3,undefined1 param_4);
undefined8 * FUN_140033bc0(undefined8 *param_1,ulonglong param_2,undefined8 param_3,size_t param_4);
void FUN_140033d50(undefined8 param_1,undefined8 param_2,longlong *param_3);
void FUN_140033db0(undefined8 *param_1,void *param_2,size_t param_3);
void FUN_140033eb0(longlong *param_1);
void FUN_140033f20(longlong *param_1);
void FUN_140033f50(longlong *param_1);
void FUN_140033f70(longlong param_1);
void FUN_140033fa0(undefined8 *param_1);
void FUN_140034010(longlong param_1);
longlong * FUN_140034020(longlong *param_1,longlong *param_2,longlong *param_3);
void FUN_140034280(ulonglong *param_1,ulonglong param_2);
void FUN_140034310(void);
void FUN_140034500(ulonglong *param_1,ulonglong param_2);
undefined8 *FUN_140034590(undefined8 *param_1,undefined8 param_2,undefined8 *param_3,undefined8 *param_4);
undefined8 *FUN_140034780(undefined8 *param_1,undefined8 param_2,undefined8 *param_3,undefined8 *param_4);
undefined8 * FUN_1400349a0(undefined8 *param_1,ulonglong param_2);
undefined8 * FUN_1400349f0(undefined8 *param_1,ulonglong param_2);
undefined8 * FUN_140034a20(undefined8 *param_1,ulonglong param_2);
undefined8 * FUN_140034a50(undefined8 *param_1,ulonglong param_2);
void FUN_140034aa0(void);
void FUN_140034ac0(void);
void FUN_140034ae0(ulonglong *param_1,ulonglong param_2);
void FUN_140034b60(ulonglong *param_1,ulonglong param_2);
ulonglong FUN_140034bf0(undefined8 param_1,ulonglong param_2);
basic_istream<> * FUN_140034c60(basic_istream<> *param_1,longlong *param_2,uint param_3);
undefined8 * FUN_140034e00(undefined8 *param_1,void *param_2,void *param_3);
basic_ostream<> * FUN_140034f50(basic_ostream<> *param_1,char *param_2,ulonglong param_3);
undefined8 *FUN_140035110(longlong *param_1,undefined8 *param_2,ulonglong *param_3,longlong *param_4);
undefined8 * FUN_1400352b0(longlong *param_1,undefined8 *param_2,undefined8 *param_3);
void FUN_140035590(longlong *param_1,void *param_2,void *param_3,ulonglong param_4);
void FUN_140035810(int *param_1,int *param_2,longlong param_3,undefined1 param_4,undefined1 param_5);
undefined8 * FUN_140035af0(longlong *param_1,undefined8 *param_2,undefined8 *param_3);
undefined4 * FUN_140035dd0(longlong *param_1,void *param_2,undefined4 *param_3);
void FUN_140035f70(undefined8 param_1,undefined8 param_2,longlong *param_3);
undefined8 * FUN_140036030(longlong *param_1,void *param_2,undefined8 *param_3);
undefined8 * FUN_1400361d0(longlong *param_1,void *param_2,undefined8 *param_3);
longlong * FUN_1400363f0(undefined8 *param_1,longlong param_2,longlong *param_3,undefined8 param_4);
undefined8 * FUN_140036480(longlong *param_1,longlong *param_2,undefined8 *param_3);
longlong * FUN_140036730(longlong *param_1,longlong *param_2,undefined8 *param_3);
longlong * FUN_1400369e0(undefined8 *param_1,longlong param_2,longlong *param_3,undefined8 param_4);
undefined8 * FUN_140036a70(longlong *param_1,longlong *param_2,undefined8 *param_3);
longlong * FUN_140036d30(undefined8 *param_1,longlong param_2,longlong *param_3,undefined8 param_4);
undefined8 * FUN_140036dc0(longlong *param_1,void *param_2,undefined8 *param_3);
void FUN_140036fd0(longlong param_1);
undefined8 * FUN_140037050(undefined8 *param_1,ulonglong param_2);
void FUN_1400371d0(void *param_1,char param_2);
longlong FUN_1400371e0(longlong param_1);
TypeDescriptor * FUN_1400371f0(void);
void FUN_140037200(longlong param_1);
undefined8 * FUN_140037210(longlong param_1,undefined8 *param_2);
longlong * FUN_140037250(longlong *param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
void FUN_1400373b0(longlong param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
void FUN_1400373d0(void *param_1,char param_2);
TypeDescriptor * FUN_140037430(void);
ulonglong FUN_140037440(longlong param_1);
undefined8 *FUN_140037470(longlong param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
TypeDescriptor * FUN_1400374e0(void);
void FUN_1400374f0(longlong param_1);
undefined8 * FUN_140037500(longlong param_1,undefined8 *param_2);
void FUN_140037520(void *param_1,char param_2);
TypeDescriptor * FUN_1400375a0(void);
void FUN_1400375b0(longlong param_1);
undefined8 * FUN_1400375d0(longlong param_1,undefined8 *param_2);
undefined8 * FUN_140037610(longlong param_1,undefined8 *param_2);
void FUN_140037650(longlong param_1);
longlong FUN_1400376c0(undefined8 param_1,undefined8 *param_2,undefined8 *param_3);
undefined8 *FUN_140037740(undefined8 *param_1,ulonglong param_2,undefined8 param_3,undefined8 param_4);
void FUN_140037820(undefined8 *param_1);
undefined8 * FUN_140037870(undefined8 *param_1,ulonglong param_2);
void FUN_1400378a0(longlong *param_1);
void FUN_140037a40(longlong *param_1,void *param_2);
ulonglong * FUN_140037b50(ulonglong *param_1,int *param_2,int *param_3);
longlong *FUN_140037cc0(undefined8 *param_1,undefined8 *param_2,longlong param_3,undefined8 param_4);
void FUN_140037db0(longlong *param_1);
void * FUN_140037e60(void *param_1,uint param_2);
void * FUN_140037ea0(void *param_1,uint param_2);
undefined8 * FUN_140037ee0(undefined8 *param_1,longlong param_2,undefined8 *param_3);
undefined8 * FUN_140037fa0(undefined8 *param_1,undefined4 *param_2);
longlong * FUN_140038070(longlong *param_1,undefined *param_2,undefined8 *param_3);
void FUN_140038130(int *param_1,int *param_2,int *param_3);
undefined8 * FUN_140038280(undefined8 *param_1,ulonglong param_2);
longlong * FUN_1400382f0(longlong *param_1,undefined *param_2,undefined8 *param_3);
void FUN_1400385c0(void *param_1,char param_2);
TypeDescriptor * FUN_1400385d0(void);
longlong * FUN_1400385e0(longlong param_1,longlong *param_2);
undefined8 * FUN_140038600(longlong param_1,undefined8 *param_2);
void FUN_140038630(longlong param_1,undefined8 param_2);
void FUN_140038650(undefined8 *param_1,undefined4 *param_2);
undefined4 * FUN_140038670(undefined4 *param_1,undefined4 *param_2);
void FUN_140038690(longlong param_1);
void FUN_1400387f0(undefined8 *param_1);
void FUN_140038870(undefined4 *param_1,undefined4 *param_2);
undefined8 * FUN_140038880(undefined8 *param_1,uint param_2);
undefined8 * FUN_1400388c0(undefined8 *param_1,uint param_2);
TypeDescriptor * FUN_140038900(void);
void FUN_140038910(longlong param_1);
undefined8 * FUN_140038920(longlong param_1,undefined8 *param_2);
void FUN_140038938(longlong param_1,uint param_2);
void FUN_140038944(longlong param_1,uint param_2);
void FUN_140038950(longlong param_1,uint param_2);
void FUN_14003895c(longlong param_1,uint param_2);
void FUN_140038968(longlong param_1,uint param_2);
void FUN_140038974(longlong param_1,uint param_2);
void FUN_140038980(longlong param_1,uint param_2);
int * FUN_140038990(int *param_1,int param_2,int param_3,undefined4 param_4);
void FUN_140038a60(uint *param_1,float param_2);
int FUN_140038c10(int param_1,int param_2);
uint FUN_140038d00(longlong param_1);
void FUN_140039390(longlong *param_1);
void FUN_140039410(undefined8 param_1,undefined8 param_2,longlong *param_3);
uint FUN_140039460(uint *param_1);
longlong * FUN_1400395f0(longlong *param_1,longlong *param_2,longlong *param_3,int *param_4);
double * FUN_140039880(double *param_1,double *param_2,uint param_3,undefined8 param_4,undefined8 param_5,undefined8 param_6,undefined8 param_7,longlong param_8);
double * FUN_140039bd0(double *param_1,longlong param_2,undefined4 param_3,uint param_4,undefined8 param_5,undefined8 param_6,undefined8 param_7,undefined8 param_8,longlong param_9);
double FUN_14003a050(undefined8 *param_1,byte param_2,uint *param_3,int *param_4,int *param_5,double param_6);
uint FUN_14003a150(int *param_1,int *param_2,undefined8 *param_3,byte param_4);
double FUN_14003a380(uint *param_1,int *param_2);
double FUN_14003a550(uint *param_1,int *param_2,int *param_3,double param_4,undefined8 *param_5);
double * FUN_14003a870(double *param_1,longlong param_2,undefined4 param_3,uint param_4,uint param_5,undefined8 param_6,undefined8 param_7,undefined8 param_8,undefined8 param_9,longlong param_10);
TypeDescriptor * FUN_14003aab0(void);
void FUN_14003aac0(longlong param_1,undefined8 param_2,undefined4 *param_3,undefined8 param_4,undefined8 param_5);
undefined8 * FUN_14003ab10(longlong param_1,undefined8 *param_2);
longlong * FUN_14003ab30(longlong *param_1,longlong *param_2);
longlong * FUN_14003afc0(longlong *param_1,longlong *param_2);
ulonglong FUN_14003b4d0(undefined8 param_1,ulonglong param_2);
void * FUN_14003b540(longlong *param_1,void *param_2,undefined4 *param_3);
longlong *FUN_14003b690(longlong param_1,longlong *param_2,longlong *param_3,undefined1 param_4,undefined8 param_5,undefined8 param_6,uint param_7,longlong *param_8);
undefined8 *FUN_14003bb50(uint *param_1,undefined8 *param_2,longlong *param_3,byte param_4,undefined4 param_5,undefined4 param_6,uint param_7,longlong param_8,double param_9);
void FUN_14003c560(longlong *param_1);
void FUN_14003c5c0(undefined8 *param_1);
void FUN_14003c680(longlong *param_1);
void FUN_14003c750(longlong param_1,undefined8 *param_2,char param_3);
longlong * FUN_14003c7a0(longlong *param_1,char param_2);
void FUN_14003c8e0(longlong *param_1);
void FUN_14003c9a0(undefined8 *param_1);
void FUN_14003ca40(longlong *param_1,longlong *param_2);
undefined8 * FUN_14003cab0(undefined8 *param_1,uint param_2);
undefined8 *FUN_14003caf0(undefined8 *param_1,undefined8 param_2,undefined8 *param_3,undefined4 *param_4,undefined8 *param_5);
undefined8 * FUN_14003cce0(longlong *param_1,undefined8 *param_2,undefined8 *param_3);
TypeDescriptor * FUN_14003cf30(void);
void FUN_14003cf40(longlong param_1,undefined8 *param_2,undefined8 *param_3,undefined8 param_4,undefined8 param_5,undefined8 param_6,undefined8 param_7,undefined8 param_8,undefined8 param_9);
undefined8 * FUN_14003cfa0(longlong param_1,undefined8 *param_2);
longlong * FUN_14003cfc0(longlong *param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
void FUN_14003d120(longlong param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
undefined8 *FUN_14003d140(undefined8 *param_1,ulonglong param_2,undefined8 param_3,undefined8 param_4);
void FUN_14003d220(undefined8 *param_1);
void FUN_14003d270(longlong *param_1);
void FUN_14003d380(longlong *param_1,void *param_2);
undefined8 *FUN_14003d470(undefined8 *param_1,undefined8 *param_2,undefined8 *param_3,undefined8 param_4);
undefined8 *FUN_14003d520(undefined8 *param_1,undefined8 *param_2,undefined8 param_3,undefined8 param_4);
longlong * FUN_14003d630(longlong *param_1,undefined *param_2,undefined8 *param_3);
undefined8 * FUN_14003d6f0(undefined8 *param_1,ulonglong param_2);
longlong * FUN_14003d760(longlong *param_1,undefined *param_2,undefined8 *param_3);
void FUN_14003da30(void *param_1,char param_2);
TypeDescriptor * FUN_14003da40(void);
double * FUN_14003da50(longlong param_1,double *param_2);
void FUN_14003dbe0(longlong param_1);
void FUN_14003dbf0(undefined8 *param_1);
void FUN_14003dc20(longlong param_1);
void FUN_14003dd80(undefined8 *param_1);
undefined8 * FUN_14003de00(undefined8 *param_1,uint param_2);
undefined8 * FUN_14003de40(undefined8 *param_1,uint param_2);
void FUN_14003de80(undefined8 *param_1,undefined8 *param_2);
undefined8 * FUN_14003dea0(undefined8 *param_1,undefined8 *param_2);
void FUN_14003ded0(undefined8 *param_1,undefined8 *param_2);
TypeDescriptor * FUN_14003dee0(void);
void FUN_14003def0(longlong param_1);
undefined8 * FUN_14003df00(longlong param_1,undefined8 *param_2);
ulonglong * FUN_14003df20(ulonglong *param_1,longlong param_2,undefined8 param_3,undefined4 param_4);
longlong * FUN_14003e1a0(longlong *param_1,longlong param_2,undefined8 param_3);
void FUN_14003e330(int *param_1,uint param_2,undefined8 *param_3);
void FUN_14003e5c0(int *param_1,int *param_2,undefined8 *param_3);
longlong * FUN_14003e690(longlong *param_1,uint param_2,uint param_3,uint param_4,uint param_5);
longlong * FUN_14003e8b0(longlong *param_1,undefined8 *param_2);
void FUN_14003ee70(longlong *param_1);
longlong * FUN_14003eea0(longlong *param_1,longlong param_2,int param_3,int param_4);
longlong * FUN_14003f120(longlong *param_1,longlong param_2,int param_3,int param_4);
longlong * FUN_14003f3a0(longlong *param_1,longlong param_2,int param_3,int param_4);
longlong * FUN_14003f570(longlong *param_1,longlong param_2,int param_3,int param_4);
longlong * FUN_14003f820(longlong *param_1,longlong param_2,int param_3,int param_4);
longlong * FUN_14003fc30(longlong *param_1,longlong param_2,int param_3,int param_4);
longlong * FUN_14003fde0(longlong *param_1,longlong param_2,undefined8 param_3,int param_4);
longlong * FUN_14003ff30(longlong *param_1,longlong param_2,undefined8 param_3,int param_4);
longlong * FUN_140040070(longlong *param_1,longlong param_2,int param_3,int param_4);
void FUN_1400402a0(longlong *param_1,void *param_2,void *param_3,ulonglong param_4);
undefined8 * FUN_140040530(longlong *param_1,undefined8 *param_2,int *param_3);
void FUN_140040660(undefined8 param_1,undefined8 param_2,longlong *param_3);
void * FUN_140040720(longlong *param_1,void *param_2,undefined8 *param_3);
undefined8 * FUN_1400408c0(longlong *param_1,void *param_2,undefined8 *param_3);
void FUN_140040a60(longlong *param_1,longlong param_2,longlong param_3,longlong param_4);
void FUN_140040b30(undefined8 param_1,undefined8 param_2,longlong *param_3);
longlong * FUN_140040b80(longlong *param_1,undefined8 *param_2,int param_3,int param_4);
undefined8 *FUN_140040cc0(longlong *param_1,undefined8 *param_2,undefined4 *param_3,undefined ***param_4,longlong *param_5,longlong *param_6);
void FUN_140040eb0(undefined8 *param_1);
undefined8 * FUN_140040ee0(longlong param_1,undefined8 *param_2);
undefined8 FUN_1400410f0(void);
void FUN_140041100(longlong *param_1,longlong *param_2);
undefined8 * FUN_140041240(undefined8 *param_1,ulonglong param_2);
undefined8 * FUN_140041270(longlong param_1,undefined8 *param_2);
undefined8 FUN_140041490(void);
undefined8 * FUN_1400414a0(undefined8 *param_1,ulonglong param_2);
undefined8 * FUN_1400414d0(longlong param_1,undefined8 *param_2);
undefined8 FUN_1400416f0(void);
undefined8 * FUN_140041700(undefined8 *param_1,ulonglong param_2);
void * FUN_140041730(void *param_1,uint param_2);
undefined8 * FUN_1400417d0(longlong param_1,undefined8 *param_2);
undefined8 FUN_1400419f0(void);
void FUN_140041a00(ulonglong *param_1,undefined4 *param_2,ulonglong param_3);
undefined8 * FUN_140041b90(undefined8 *param_1,ulonglong param_2);
undefined8 * FUN_140041bc0(longlong param_1,undefined8 *param_2);
undefined8 FUN_140041e00(void);
undefined8 * FUN_140041e10(undefined8 *param_1,ulonglong param_2);
undefined8 * FUN_140041e40(longlong param_1,undefined8 *param_2);
undefined8 FUN_140042060(void);
undefined8 * FUN_140042070(longlong param_1,undefined8 *param_2);
undefined8 FUN_1400422a0(void);
undefined8 * FUN_1400422b0(longlong param_1,undefined8 *param_2);
undefined8 FUN_1400424e0(void);
undefined8 * FUN_1400424f0(undefined8 *param_1,ulonglong param_2);
void FUN_140042520(longlong *param_1,undefined4 param_2,undefined4 param_3);
undefined8 * FUN_140043000(undefined8 *param_1,uint param_2);
undefined8 * FUN_140043380(undefined8 *param_1,uint param_2);
void FUN_140043580(void);
undefined8 * FUN_1400435a0(undefined8 *param_1,ulonglong param_2);
void FUN_1400435d0(void *param_1,char param_2);
longlong * FUN_1400435f0(longlong param_1,longlong *param_2);
undefined8 * FUN_140043670(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043690(void);
longlong * FUN_1400436a0(longlong param_1,longlong *param_2,longlong param_3);
undefined8 * FUN_1400436d0(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_1400436f0(void);
void FUN_140043700(longlong param_1,longlong param_2);
undefined8 * FUN_140043720(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043740(void);
void FUN_140043750(longlong param_1,longlong param_2);
undefined8 * FUN_140043770(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043790(void);
longlong * FUN_1400437a0(longlong param_1,longlong *param_2,longlong param_3);
undefined8 * FUN_1400437d0(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_1400437f0(void);
void FUN_140043800(longlong param_1,longlong param_2);
undefined8 * FUN_140043820(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043840(void);
void FUN_140043850(longlong param_1,longlong param_2);
undefined8 * FUN_140043870(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043890(void);
longlong * FUN_1400438a0(longlong param_1,longlong *param_2,longlong param_3);
undefined8 * FUN_1400438d0(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_1400438f0(void);
void FUN_140043900(longlong param_1,longlong param_2);
undefined8 * FUN_140043920(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043940(void);
void FUN_140043950(longlong param_1,longlong param_2);
undefined8 * FUN_140043970(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043990(void);
longlong * FUN_1400439a0(longlong param_1,longlong *param_2,longlong param_3);
undefined8 * FUN_1400439d0(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_1400439f0(void);
void FUN_140043a00(longlong param_1,longlong param_2);
undefined8 * FUN_140043a20(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043a40(void);
void FUN_140043a50(longlong param_1,longlong param_2);
undefined8 * FUN_140043a70(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043a90(void);
longlong * FUN_140043aa0(longlong param_1,longlong *param_2,longlong param_3);
undefined8 * FUN_140043ad0(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043af0(void);
void FUN_140043b00(longlong param_1,longlong param_2);
undefined8 * FUN_140043b20(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043b40(void);
void FUN_140043b50(longlong param_1,longlong param_2);
undefined8 * FUN_140043b70(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043b90(void);
longlong * FUN_140043ba0(longlong param_1,longlong *param_2,longlong param_3);
undefined8 * FUN_140043bd0(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043bf0(void);
void FUN_140043c00(longlong param_1,longlong param_2);
undefined8 * FUN_140043c20(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043c40(void);
void FUN_140043c50(longlong param_1,longlong param_2);
undefined8 * FUN_140043c70(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043c90(void);
longlong * FUN_140043ca0(longlong param_1,longlong *param_2,longlong param_3);
undefined8 * FUN_140043cd0(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043cf0(void);
void FUN_140043d00(longlong param_1,longlong param_2);
undefined8 * FUN_140043d20(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043d40(void);
void FUN_140043d50(longlong param_1,longlong param_2);
undefined8 * FUN_140043d70(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043d90(void);
longlong * FUN_140043da0(longlong param_1,longlong *param_2,longlong param_3);
undefined8 * FUN_140043dd0(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043df0(void);
void FUN_140043e00(longlong param_1,longlong param_2);
undefined8 * FUN_140043e20(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043e40(void);
void FUN_140043e50(longlong param_1,longlong param_2);
undefined8 * FUN_140043e70(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043e90(void);
longlong * FUN_140043ea0(longlong param_1,longlong *param_2,longlong param_3);
undefined8 * FUN_140043ed0(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043ef0(void);
undefined8 * FUN_140043f00(longlong param_1,undefined8 *param_2);
TypeDescriptor * FUN_140043f20(void);
void FUN_140043f30(longlong param_1,longlong param_2);
undefined8 * FUN_140043f50(longlong param_1,undefined8 *param_2);
void FUN_140043f70(longlong param_1,int param_2,int param_3);
void FUN_140044030(longlong param_1,int param_2,int param_3);
void FUN_140044160(longlong param_1,int param_2,int param_3);
void FUN_1400443f0(longlong param_1,int param_2,int param_3);
void FUN_1400445c0(longlong param_1,int param_2,int param_3);
void FUN_140044680(longlong param_1,int param_2,int param_3);
void FUN_1400447f0(longlong param_1,int param_2,int param_3);
void FUN_140044940(longlong param_1,int param_2,int param_3);
void FUN_140044ae0(longlong param_1,int param_2,int param_3);
void FUN_140044d20(longlong param_1,int param_2,int param_3);
void FUN_140044f60(longlong param_1,int param_2,int param_3);
void FUN_140045240(longlong param_1,int param_2,int param_3);
void FUN_140045500(longlong param_1,int param_2,int param_3);
void FUN_1400456b0(longlong param_1,int param_2,int param_3);
void FUN_140045a90(longlong param_1,int param_2,int param_3);
void FUN_140045df0(longlong param_1,int param_2,int param_3);
void FUN_140046130(longlong param_1,int param_2,int param_3);
void FUN_140046500(ulonglong *param_1,ulonglong *param_2);
void FUN_1400465a0(longlong *param_1);
undefined8 * FUN_140046630(longlong param_1,undefined8 *param_2);
undefined8 FUN_140046870(void);
undefined8 * FUN_140046880(undefined8 *param_1,undefined8 *param_2);
void FUN_140046960(undefined8 *param_1);
undefined * FUN_140046a80(void);
int __cdecl sscanf(char *_Src,char *_Format,...);
void FUN_140046af0(undefined2 *param_1);
undefined2 * FUN_140046b90(undefined2 *param_1);
void FUN_140047790(longlong param_1);
void FUN_1400477c0(longlong param_1);
void FUN_1400477f0(longlong param_1);
void FUN_140047820(longlong param_1);
void FUN_140047880(longlong param_1);
void FUN_140047900(longlong param_1);
void FUN_140047930(longlong param_1);
float * FUN_140047960(longlong *param_1,float *param_2);
longlong FUN_140047a20(longlong param_1,uint param_2);
undefined4 * FUN_140047ac0(undefined4 *param_1);
undefined8 * FUN_140047cb0(undefined8 *param_1);
void FUN_140047ed0(longlong param_1,int param_2);
void FUN_140047f90(longlong param_1,uint param_2,byte param_3,float param_4);
void FUN_140048130(longlong param_1,float param_2,float param_3);
void FUN_1400482d0(longlong param_1,int param_2,byte param_3);
void FUN_140048400(longlong param_1,float param_2,float param_3);
int FUN_1400484e0(longlong param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
uint FUN_140048560(byte *param_1,ulonglong param_2,uint param_3);
FILE * FUN_140048610(LPCSTR param_1,LPCSTR param_2);
void * FUN_140048740(LPCSTR param_1,undefined8 param_2,size_t *param_3);
int FUN_140048880(uint *param_1,byte *param_2,byte *param_3);
uint FUN_140048a30(float *param_1);
void FUN_140048ae0(int *param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
void FUN_140048b10(int *param_1,undefined8 param_2,undefined8 param_3);
void FUN_140048c40(int *param_1,longlong param_2,int param_3,int param_4);
void FUN_140048d70(undefined8 param_1,uint param_2);
void FUN_140048e30(void);
void FUN_140048ee0(undefined8 param_1,byte *param_2,byte *param_3,char param_4);
void FUN_140049220(undefined8 param_1,byte *param_2,byte *param_3,float param_4);
void FUN_140049530(int *param_1,float *param_2,float *param_3,byte *param_4,byte *param_5,undefined8 *param_6,float *param_7,float *param_8);
void FUN_1400498b0(float *param_1,float *param_2,byte *param_3,undefined8 param_4,undefined8 *param_5,float *param_6,float *param_7);
void FUN_140049b50(undefined8 param_1,undefined8 param_2,uint param_3,char param_4,float param_5);
void FUN_140049cf0(undefined8 param_1,undefined8 param_2,float param_3);
void FUN_140049e40(float *param_1,int param_2,uint param_3);
void FUN_14004a230(undefined8 param_1,float param_2,uint param_3);
void FUN_14004a7a0(void);
void FUN_14004abe0(void);
longlong * FUN_14004b5c0(longlong *param_1,longlong param_2,byte *param_3);
void FUN_14004ba50(longlong param_1);
void FUN_14004bad0(longlong param_1);
uint FUN_14004bc60(longlong *param_1,uint param_2);
void FUN_14004bd00(uint param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
ulonglong FUN_14004be60(void);
bool FUN_14004bf70(float *param_1,uint param_2,uint param_3,undefined8 param_4);
uint * FUN_14004c150(longlong param_1,longlong param_2,undefined8 param_3);
void FUN_14004c300(longlong param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
void FUN_14004c3c0(undefined8 param_1,ulonglong param_2,undefined8 param_3,ulonglong param_4);
void FUN_14004c620(void);
void FUN_14004ca40(undefined8 param_1,void *param_2,size_t *param_3,FILE *param_4);
void FUN_14004ddd0(int *param_1,longlong param_2);
void FUN_14004dea0(longlong param_1,int param_2);
void FUN_14004df60(float *param_1,float *param_2,char param_3);
void FUN_14004dff0(void);
void FUN_14004e0a0(longlong param_1,uint param_2);
void FUN_14004e2f0(void);
void FUN_14004e720(undefined *param_1,byte *param_2,double param_3,double param_4);
void FUN_14004eb10(undefined *param_1,byte *param_2,double param_3,double param_4);
void FUN_14004ef60(void);
undefined8 FUN_14004f1b0(uint param_1);
void FUN_14004f230(longlong param_1,char param_2,uint param_3);
void FUN_14004f3c0(longlong param_1,longlong param_2);
longlong * FUN_14004f540(byte *param_1,uint param_2);
float * FUN_14004f740(float *param_1,longlong *param_2,undefined8 *param_3);
void FUN_14004f980(longlong param_1,float *param_2,float *param_3);
undefined8 * FUN_14004fa90(undefined8 *param_1,longlong *param_2,float *param_3);
float * FUN_14004fcf0(float *param_1,longlong param_2,int param_3,float param_4,float param_5);
ulonglong FUN_14004fe30(longlong *param_1,undefined8 *param_2,uint *param_3,int param_4,uint *param_5,undefined8 *param_6);
void FUN_140050a30(longlong *param_1);
void FUN_140050e10(longlong *param_1,float *param_2,byte param_3,undefined8 param_4,int param_5,uint *param_6,float param_7);
void FUN_1400514f0(longlong *param_1,float *param_2,byte *param_3,undefined8 param_4);
undefined8 FUN_140051940(byte *param_1,undefined8 param_2,uint param_3);
void FUN_140053c20(void);
void FUN_140053e40(longlong param_1,ulonglong param_2,undefined8 param_3,undefined8 param_4);
void FUN_140054290(longlong param_1);
void FUN_140054330(undefined4 param_1);
void FUN_1400543d0(longlong param_1,float *param_2,uint param_3);
void FUN_140054540(longlong param_1,float *param_2,uint param_3);
void FUN_140054640(void);
void FUN_1400547b0(void);
longlong FUN_140054860(longlong param_1,uint param_2);
char * FUN_140054930(uint param_1);
int FUN_1400549f0(uint param_1,float param_2,float param_3);
void FUN_140054a90(short *param_1);
short * FUN_140054c60(uint param_1);
bool FUN_140054e20(uint param_1,int param_2,uint param_3);
bool FUN_140054f50(uint param_1,int param_2,uint param_3);
bool FUN_140055030(int param_1,int param_2,byte param_3);
undefined8 FUN_1400550e0(undefined8 *param_1,undefined8 *param_2,char param_3);
ulonglong FUN_1400551b0(void);
void FUN_140055260(void);
void FUN_1400558b0(void);
longlong FUN_140055c80(float *param_1);
void FUN_140055e10(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
void FUN_1400564b0(undefined8 param_1,int *param_2,undefined8 param_3,undefined8 param_4);
void FUN_140056700(char param_1,undefined8 param_2,undefined8 param_3,longlong param_4);
bool FUN_140056d80(uint param_1,int param_2);
bool FUN_140056e40(uint param_1,int param_2);
void FUN_140056f40(float *param_1,float param_2);
ulonglong FUN_1400570b0(float *param_1,undefined8 param_2,float *param_3,undefined8 param_4);
void FUN_140057260(float param_1,float param_2);
ulonglong * FUN_140057310(ulonglong *param_1,ulonglong param_2,float param_3,undefined4 param_4);
float * FUN_140057410(float *param_1,longlong param_2);
float * FUN_1400575e0(float *param_1,longlong param_2,float *param_3,ulonglong param_4);
undefined8 FUN_140057ac0(uint param_1);
void FUN_140057c80(char *param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
void FUN_140057cd0(uint param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
void FUN_140057f20(longlong param_1,byte param_2,ulonglong *param_3);
void FUN_140058030(uint param_1,byte param_2,ulonglong *param_3,undefined8 param_4);
void FUN_1400581c0(void);
float * FUN_1400582a0(float *param_1,float *param_2,float *param_3,uint *param_4,float *param_5,float *param_6,uint param_7);
float * FUN_140058650(float *param_1);
float * FUN_140058730(float *param_1,longlong param_2);
void FUN_1400589c0(int param_1,longlong param_2,undefined8 param_3,undefined8 param_4);
ulonglong FUN_140058b60(longlong param_1);
void FUN_140058fd0(undefined8 param_1,undefined8 param_2,ulonglong param_3,undefined8 param_4);
void FUN_1400594b0(int param_1,uint param_2,uint param_3);
void FUN_1400597b0(undefined4 param_1,undefined4 param_2,uint param_3,undefined4 param_4);
void FUN_140059910(longlong *param_1);
void FUN_1400599e0(int param_1);
void FUN_140059b10(longlong param_1,char param_2);
float * FUN_140059cb0(float *param_1);
void FUN_140059ef0(undefined8 param_1,undefined8 param_2,ulonglong param_3,ulonglong param_4);
void FUN_14005aa20(undefined8 param_1,undefined8 param_2,ulonglong param_3,ulonglong param_4);
void FUN_14005b580(void);
void FUN_14005ba50(void);
undefined8 FUN_14005bd00(void);
void FUN_14005c1d0(void);
void FUN_14005c410(int param_1);
void FUN_14005c560(void);
void FUN_14005cf50(void);
void FUN_14005d270(void);
void FUN_14005d330(longlong param_1,undefined8 param_2,undefined8 param_3);
void FUN_14005d400(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
void FUN_14005d440(longlong param_1,char *param_2,char *param_3,ulonglong param_4);
void FUN_14005d640(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
void FUN_14005d730(undefined8 *param_1);
longlong FUN_14005d860(byte *param_1);
void FUN_14005d900(void *param_1,size_t param_2);
undefined * FUN_14005db60(longlong *param_1);
uint * FUN_14005dc60(byte *param_1);
int * FUN_14005dd50(longlong param_1);
void FUN_14005ddd0(longlong param_1);
uint * FUN_14005de50(undefined8 param_1,undefined8 param_2,byte *param_3);
void FUN_14005df30(undefined8 param_1,undefined8 param_2,longlong param_3,char *param_4);
void FUN_14005e010(longlong param_1);
void FUN_14005e160(longlong param_1,undefined8 *param_2,int *param_3);
undefined8 FUN_14005e3e0(longlong param_1);
void FUN_14005e540(undefined8 param_1,LPCSTR param_2);
void FUN_14005e610(longlong param_1,longlong param_2);
void FUN_14005e6f0(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
void FUN_14005e7d0(void);
void FUN_14005e990(uint param_1,int param_2,ulonglong param_3);
void FUN_14005ebb0(longlong param_1);
void FUN_14005ebe0(undefined8 *param_1);
void FUN_14005ecf0(undefined8 *param_1);
void FUN_14005ed50(undefined8 *param_1);
void FUN_14005ee10(undefined8 *param_1);
void FUN_14005ee70(int *param_1,undefined8 *param_2);
void FUN_14005eef0(int *param_1);
void FUN_14005efd0(int *param_1,undefined8 *param_2);
void FUN_14005f0c0(int *param_1,undefined8 *param_2);
void FUN_14005f1b0(int *param_1,int param_2);
void FUN_14005f240(int *param_1,undefined8 *param_2);
void FUN_14005f310(int *param_1,int param_2);
void FUN_14005f3f0(int *param_1,int param_2);
longlong FUN_14005f490(int *param_1,longlong param_2,undefined8 *param_3);
void FUN_14005f5a0(int *param_1,int param_2);
void FUN_14005f630(int *param_1,int param_2);
void FUN_14005f6c0(longlong param_1);
longlong FUN_14005f730(longlong param_1);
void FUN_14005f7e0(int *param_1,int param_2);
void FUN_14005f870(int *param_1,int param_2);
void FUN_14005f900(int *param_1,int param_2);
void FUN_14005f990(int *param_1,int param_2);
void FUN_14005fa30(int *param_1,int param_2);
void FUN_14005fac0(int *param_1,int param_2);
void FUN_14005fb50(longlong param_1);
void FUN_140060290(int *param_1,int param_2,int param_3,longlong param_4,int param_5);
int * FUN_140060460(int *param_1,int *param_2,int param_3,int param_4);
undefined8 FUN_140060860(int *param_1,void *param_2,int param_3);
ulonglong FUN_140060a50(longlong *param_1);
longlong * FUN_140060a70(longlong *param_1,longlong *param_2);
uint FUN_140060ba0(longlong *param_1);
longlong * FUN_140060de0(longlong *param_1,longlong *param_2,uint param_3);
longlong * FUN_140060fc0(longlong *param_1,longlong *param_2,int param_3);
int FUN_140061120(char *param_1,int param_2);
longlong * FUN_140061260(longlong *param_1,longlong *param_2,longlong *param_3);
undefined8 FUN_1400613d0(longlong param_1,longlong param_2,uint param_3);
uint FUN_140061ce0(longlong param_1,uint param_2);
int FUN_140062060(longlong param_1,int param_2);
int FUN_140062140(longlong param_1,int param_2,int param_3,int param_4,undefined2 param_5,undefined2 param_6,int param_7,int param_8,int param_9,int param_10);
void * FUN_140062230(longlong param_1,int param_2,undefined8 *param_3);
void FUN_140062f20(int *param_1,char param_2,int param_3,int param_4,int param_5,int param_6,int param_7,int param_8);
void FUN_140063050(int *param_1);
void FUN_140063100(int *param_1,float param_2,float param_3);
void FUN_1400631c0(int *param_1,float param_2,float param_3);
longlong * FUN_140063260(longlong *param_1,longlong param_2,int param_3);
undefined8 FUN_140063430(longlong param_1,int param_2,int *param_3);
void * FUN_140064670(longlong param_1,int param_2,undefined8 *param_3);
void FUN_140064770(longlong param_1,int param_2,float param_3,float param_4,float param_5,float param_6,int *param_7,int *param_8,int *param_9,int *param_10);
void FUN_1400649d0(longlong param_1,int param_2,longlong param_3,float param_4,float param_5,float param_6,float param_7);
void FUN_140064b10(longlong param_1,longlong param_2,int param_3,longlong *param_4,float param_5);
void FUN_140065150(int *param_1,float *param_2,int param_3,undefined8 param_4,int param_5,int param_6);
void FUN_140065650(undefined8 *param_1,uint param_2);
void FUN_140065830(int *param_1,longlong param_2,int *param_3,uint param_4,float param_5,float param_6,float param_7,float param_8,int param_9,int param_10);
undefined8 FUN_140065bb0(longlong param_1,int *param_2,float param_3,float param_4,float param_5,float param_6,float param_7,float param_8,float param_9,int param_10);
void FUN_140065da0(longlong param_1,int *param_2,float param_3,float param_4,float param_5,float param_6,float param_7,float param_8,float param_9,float param_10,float param_11,int param_12);
void * FUN_140066240(longlong param_1,int param_2,float param_3,longlong *param_4,int *param_5);
void FUN_140066640(byte *param_1,int param_2,uint param_3,int param_4,uint param_5);
void FUN_1400668f0(longlong param_1,uint param_2,int param_3,int param_4,uint param_5);
undefined4 FUN_140066b90(longlong param_1,longlong param_2,float *param_3,undefined8 param_4,longlong param_5);
void FUN_140067290(longlong param_1);
void FUN_1400677b0(uint *param_1);
void FUN_140067d10(undefined8 *param_1);
void FUN_140067e40(int *param_1);
void FUN_140067f00(int *param_1);
void FUN_140067fb0(int *param_1);
uint FUN_140068060(longlong param_1,float param_2);
void FUN_1400680f0(int *param_1,float *param_2,float *param_3,char param_4);
void FUN_140068200(int *param_1,undefined8 param_2);
void FUN_140068280(int *param_1,int param_2,int param_3);
void FUN_1400683a0(longlong param_1,undefined8 *param_2,undefined8 *param_3,undefined8 *param_4,undefined8 *param_5,undefined4 param_6);
void FUN_1400684f0(int *param_1,float *param_2,uint param_3,uint param_4,byte param_5,float param_6);
void FUN_140069460(int *param_1,undefined8 *param_2,uint param_3,uint param_4);
void FUN_140069a20(longlong param_1,float *param_2,float param_3,uint param_4,int param_5);
void FUN_140069cf0(longlong param_1,float *param_2,float param_3,float param_4,float param_5,int param_6);
void FUN_140069eb0(longlong param_1,float *param_2,float param_3,int param_4,int param_5);
void FUN_140069f50(longlong param_1,float *param_2,float param_3,float param_4,float param_5,int param_6);
void FUN_14006a380(longlong param_1,float *param_2,float *param_3,float param_4,uint param_5);
void FUN_14006a8c0(int *param_1,float *param_2,float *param_3,uint param_4,float param_5);
void FUN_14006aa20(int *param_1,float *param_2,float *param_3,uint param_4,float param_5,undefined8 param_6,float param_7);
void FUN_14006ab30(int *param_1,float *param_2,float *param_3,uint param_4,float param_5,uint param_6);
void FUN_14006ace0(int *param_1,undefined8 *param_2,undefined8 *param_3,undefined8 *param_4,uint param_5);
void FUN_14006ae30(int *param_1,longlong param_2,undefined8 *param_3,undefined8 *param_4,undefined8 *param_5,undefined8 *param_6,uint param_7);
void FUN_14006aef0(int *param_1);
void FUN_14006b000(int *param_1,uint *param_2);
void FUN_14006b3d0(int *param_1,int *param_2,int param_3);
void FUN_14006b4b0(longlong param_1,int *param_2,int *param_3);
void FUN_14006b550(longlong param_1);
void FUN_14006b760(longlong param_1,undefined8 *param_2,undefined4 *param_3,undefined4 *param_4);
undefined8 FUN_14006b9c0(longlong param_1,undefined8 *param_2);
void FUN_14006bc90(longlong param_1,byte *param_2,undefined8 param_3,float param_4,undefined8 *param_5,longlong param_6);
undefined8 FUN_14006bf90(longlong param_1,char *param_2,float param_3,undefined8 *param_4,longlong param_5);
undefined8 FUN_14006c120(byte *param_1);
void FUN_14006d520(longlong param_1,int *param_2);
void FUN_14006d670(longlong param_1,int param_2,int param_3);
void FUN_14006d710(longlong param_1,int param_2,int param_3);
void FUN_14006dac0(byte *param_1);
void FUN_14006dc00(byte *param_1,ulonglong param_2);
void FUN_14006de10(undefined8 *param_1);
void FUN_14006de90(undefined8 *param_1);
longlong FUN_14006df40(int *param_1);
void FUN_14006e4b0(int *param_1,int param_2);
void FUN_14006e5a0(longlong param_1,longlong param_2,ushort param_3,float param_4,float param_5,float param_6,float param_7,undefined4 param_8,undefined4 param_9,undefined4 param_10,undefined4 param_11,float param_12);
byte * FUN_14006e7b0(int *param_1,float param_2,byte *param_3,byte *param_4,float param_5);
float * FUN_14006e940(int *param_1,float *param_2,float param_3,float param_4,float param_5,byte *param_6,byte *param_7);
void FUN_14006eb60(int *param_1,int *param_2,float param_3,float *param_4,float param_5,float *param_6,byte *param_7,byte *param_8,float param_9,char param_10);
void FUN_14006f230(int *param_1,undefined8 param_2,uint param_3,int param_4,float param_5);
void FUN_14006f3e0(int *param_1,undefined8 param_2,uint param_3);
byte * FUN_14006f470(byte *param_1);
void FUN_14006fa30(int *param_1,int param_2);
void FUN_14006fb20(int *param_1,undefined8 *param_2);
void FUN_14006fc00(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
ulonglong FUN_14006fc60(undefined8 param_1,undefined8 param_2,int *param_3,int *param_4);
void FUN_14006ffa0(longlong param_1,undefined4 param_2,undefined4 param_3,undefined4 param_4);
void FUN_140070280(longlong param_1);
bool FUN_1400708f0(ulonglong param_1,undefined8 param_2);
undefined8 FUN_140070a50(void);
ulonglong FUN_140070f10(undefined8 param_1);
ulonglong FUN_1400710c0(void);
void FUN_140071230(void);
void FUN_140071880(void);
undefined8 FUN_140071c00(longlong param_1);
undefined8 FUN_140072150(HWND param_1,uint param_2,ulonglong param_3,ulonglong param_4);
void FUN_140072d70(undefined8 *param_1,undefined4 param_2,undefined2 param_3,int param_4);
longlong FUN_140072ee0(undefined4 param_1,int param_2);
void FUN_140072f90(longlong param_1);
int * FUN_140073080(undefined8 param_1,undefined8 param_2,char *param_3);
void FUN_140073180(undefined8 param_1,undefined8 param_2,longlong param_3,char *param_4);
void FUN_140073400(longlong param_1,undefined8 *param_2,int *param_3);
void FUN_1400737b0(void);
void FUN_1400739a0(int param_1,float param_2);
void FUN_140073ad0(void);
void FUN_140074030(byte *param_1,byte *param_2);
void FUN_140074710(char *param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
void FUN_140074740(char *param_1,undefined8 *param_2);
void FUN_140074850(undefined8 *param_1,char *param_2,undefined8 param_3,undefined8 param_4);
char FUN_140074900(float *param_1,uint param_2,char *param_3,undefined1 *param_4,uint param_5);
ulonglong FUN_140075030(byte *param_1,ulonglong *param_2);
char FUN_140075380(uint param_1,float *param_2);
uint FUN_140075620(longlong *param_1,int param_2);
void FUN_1400756a0(int param_1);
ulonglong FUN_140075860(float *param_1,undefined8 param_2,int param_3,longlong *param_4,longlong param_5,longlong param_6,uint param_7);
void FUN_140075e50(longlong param_1,float *param_2,undefined8 *param_3,undefined8 *param_4,float *param_5,float *param_6);
ulonglong FUN_1400762d0(byte *param_1,byte *param_2);
ulonglong FUN_140076a10(int param_1,float *param_2);
void FUN_140076da0(int param_1);
ulonglong FUN_140076e80(byte *param_1,char param_2,undefined8 param_3,float *param_4);
void FUN_140077400(longlong param_1);
DWORD Create_symlink(LPCWSTR param_1,LPCWSTR param_2,uint param_3);
DWORD FUN_14007759c(HANDLE param_1,ulonglong *param_2);
DWORD Get_last_write_time_by_handle(HANDLE param_1,undefined8 *param_2);
DWORD FUN_140077688(HANDLE param_1);
void FUN_140077700(HANDLE param_1);
ulonglong FUN_140077720(void);
undefined8 __std_fs_convert_narrow_to_wide(UINT param_1,LPCSTR param_2,int param_3,LPWSTR param_4,int param_5);
undefined8 __std_fs_convert_wide_to_narrow(UINT param_1,LPCWSTR param_2,int param_3,LPSTR param_4,int param_5);
undefined8 FUN_1400778b4(UINT param_1,LPCWSTR param_2,int param_3,LPSTR param_4,int param_5);
undefined8 FUN_140077980(LPCWSTR param_1,LPCWSTR param_2,uint param_3);
undefined8 __std_fs_create_directory(LPCWSTR param_1);
void FUN_140077c80(LPCWSTR param_1,LPCWSTR param_2);
void FUN_140077c8c(LPCWSTR param_1,LPCWSTR param_2);
DWORD FUN_140077c94(HANDLE param_1,LPWIN32_FIND_DATAW param_2);
void FUN_140077cb4(HANDLE param_1);
DWORD __std_fs_directory_iterator_open(LPCWSTR param_1,longlong *param_2,LPVOID param_3);
undefined8 __std_fs_get_current_path(DWORD param_1,LPWSTR param_2);
DWORD __std_fs_get_file_attributes_by_handle(HANDLE param_1,undefined4 *param_2);
DWORD FUN_140077dd8(ulonglong *param_1,LPCWSTR param_2);
DWORD FUN_140077e54(LPCWSTR param_1,ulonglong *param_2,uint param_3,uint param_4);
bool FUN_14007817c(int *param_1);
DWORD __std_fs_open_handle(undefined8 *param_1,LPCWSTR param_2,DWORD param_3,DWORD param_4);
undefined8 FUN_1400781e0(int *param_1,longlong *param_2,ushort *param_3);
DWORD FUN_14007825c(HANDLE param_1,LPVOID param_2,DWORD param_3);
undefined8 FUN_14007829c(LPCWSTR param_1);
DWORD FUN_1400784c0(LPCWSTR param_1);
DWORD FUN_1400784e0(HANDLE param_1,LPVOID param_2);
ulonglong FUN_140078528(DWORD param_1,longlong *param_2);
HLOCAL __stdcall LocalFree(HLOCAL hMem);
undefined1 (*) [32]FUN_1400785d0(undefined1 (*param_1) [32],undefined1 (*param_2) [32],uint param_3);
ulonglong * FUN_140078680(ulonglong *param_1,ulonglong *param_2,ulonglong param_3);
void FUN_140078750(void);
void __cdecl std::_Facet_Register(_Facet_base *param_1);
void __thiscall std::basic_streambuf<>::_Lock(basic_streambuf<> *this);
void __thiscall std::basic_streambuf<>::_Unlock(basic_streambuf<> *this);
__int64 __thiscall std::basic_streambuf<>::showmanyc(basic_streambuf<> *this);
int __thiscall std::basic_streambuf<>::uflow(basic_streambuf<> *this);
__int64 __thiscall std::basic_streambuf<>::xsgetn(basic_streambuf<> *this,char *param_1,__int64 param_2);
__int64 __thiscall std::basic_streambuf<>::xsputn(basic_streambuf<> *this,char *param_1,__int64 param_2);
basic_streambuf<> * __thiscall std::basic_streambuf<>::setbuf(basic_streambuf<> *this,char *param_1,__int64 param_2);
int __thiscall std::basic_streambuf<>::sync(basic_streambuf<> *this);
void __thiscall std::basic_streambuf<>::imbue(basic_streambuf<> *this,locale *param_1);
void __thiscall std::basic_streambuf<>::_Lock(basic_streambuf<> *this);
void __thiscall std::basic_streambuf<>::_Unlock(basic_streambuf<> *this);
__int64 __thiscall std::basic_streambuf<>::showmanyc(basic_streambuf<> *this);
ushort __thiscall std::basic_streambuf<>::uflow(basic_streambuf<> *this);
__int64 __thiscall std::basic_streambuf<>::xsgetn(basic_streambuf<> *this,wchar_t *param_1,__int64 param_2);
__int64 __thiscall std::basic_streambuf<>::xsputn(basic_streambuf<> *this,wchar_t *param_1,__int64 param_2);
basic_streambuf<> * __thiscall std::basic_streambuf<>::setbuf(basic_streambuf<> *this,wchar_t *param_1,__int64 param_2);
int __thiscall std::basic_streambuf<>::sync(basic_streambuf<> *this);
void __thiscall std::basic_streambuf<>::imbue(basic_streambuf<> *this,locale *param_1);
void __cdecl __security_check_cookie(uintptr_t _StackCookie);
void __cdecl free(void *_Memory);
undefined8 FUN_140078858(void);
void FUN_140078928(void);
void _Init_thread_footer(int *param_1);
void _Init_thread_header(int *param_1);
void _Init_thread_notify(void);
void _Init_thread_wait(DWORD param_1);
void FUN_140078ac0(size_t param_1);
void __cdecl`eh_vector_destructor_iterator'(void *param_1,__uint64 param_2,__uint64 param_3,_func_void_void_ptr *param_4);
void __cdecl __ArrayUnwind(void *param_1,__uint64 param_2,__uint64 param_3,_func_void_void_ptr *param_4);
ulonglong __scrt_acquire_startup_lock(void);
longlong __scrt_initialize_crt(int param_1);
undefined8 FUN_140078c54(uint param_1);
ulonglong FUN_140078ce0(longlong param_1);
void __scrt_release_startup_lock(char param_1);
undefined1 __scrt_uninitialize_crt(undefined8 param_1,char param_2);
_onexit_t __cdecl _onexit(_onexit_t _Func);
int __cdecl atexit(_func_5014 *param_1);
void __cdecl free(void *_Memory);
void thunk_FUN_140078ac0(size_t param_1);
void thunk_FUN_14007978c(size_t param_1);
undefined8 * FUN_140078e34(undefined8 *param_1,ulonglong param_2);
void tls_callback_0(undefined8 param_1,int param_2);
void __dyn_tls_on_demand_init(void);
void __raise_securityfailure(_EXCEPTION_POINTERS *param_1);
void FUN_140078f0c(void);
void capture_previous_context(PCONTEXT param_1);
void FUN_140079054(void);
undefined8 FUN_14007910c(void);
void FUN_14007911c(void);
ulonglong FUN_140079138(void);
void entry(void);
undefined8 __GSHandlerCheck(undefined8 param_1,undefined8 param_2,undefined8 param_3,longlong param_4);
ulonglong __GSHandlerCheckCommon(undefined8 param_1,longlong param_2);
undefined8 FUN_14007933c(void);
void FUN_1400794e8(void);
void FUN_1400794f0(undefined4 param_1);
WORD __scrt_get_show_window_mode(void);
undefined8 thunk_FUN_140002070(void);
ulonglong FUN_140079680(void);
void FUN_1400796d4(void);
undefined8 FUN_1400796e4(undefined8 *param_1);
undefined8 * FUN_140079740(undefined8 *param_1);
void FUN_140079760(void);
bool __scrt_is_ucrt_dll_in_use(void);
void FUN_14007978c(size_t param_1);
void __cdecl __security_init_cookie(void);
undefined8 FUN_14007984c(void);
void FUN_140079854(void);
undefined1 FUN_140079864(void);
void FUN_140079868(void);
bool FUN_140079884(void);
undefined ** FUN_140079890(void);
undefined * FUN_140079898(void);
void FUN_1400798a0(void);
void FUN_1400798dc(void);
void __CxxFrameHandler4(void);
void _purecall(void);
void __current_exception(void);
void __current_exception_context(void);
void * __cdecl memset(void *_Dst,int _Val,size_t _Size);
void __stdcall _CxxThrowException(void *pExceptionObject,ThrowInfo *pThrowInfo);
void terminate(void);
void __cdecl free(void *_Memory);
void * __cdecl malloc(size_t _Size);
int __cdecl _callnewh(size_t _Size);
void _initialize_onexit_table(void);
void _register_onexit_function(void);
void _crt_atexit(void);
void __cdecl _cexit(void);
void _seh_filter_exe(void);
void _set_app_type(void);
void __setusermatherr(void);
void _configure_wide_argv(void);
void _initialize_wide_environment(void);
void _get_wide_winmain_command_line(void);
void _initterm(void);
void _initterm_e(void);
void __cdecl exit(int _Code);
void __cdecl _exit(int _Code);
errno_t __cdecl _set_fmode(int _Mode);
void _register_thread_local_exe_atexit_callback(void);
int __cdecl _configthreadlocale(int _Flag);
void _set_new_mode(void);
void __p__commode(void);
void FID_conflict:__GSHandlerCheck_EH(longlong param_1,undefined8 param_2,undefined8 param_3,longlong param_4);
void __chkstk(void);
void __RTDynamicCast(void);
void * __cdecl memchr(void *_Buf,int _Val,size_t _MaxCount);
int __cdecl memcmp(void *_Buf1,void *_Buf2,size_t _Size);
void * __cdecl memcpy(void *_Dst,void *_Src,size_t _Size);
void * __cdecl memmove(void *_Dst,void *_Src,size_t _Size);
float __cdecl acosf(float _X);
float __cdecl ceilf(float _X);
double __cdecl cos(double _X);
float __cdecl cosf(float _X);
double __cdecl floor(double _X);
float __cdecl fmodf(float _X,float _Y);
float __cdecl powf(float _X,float _Y);
double __cdecl sin(double _X);
float __cdecl sinf(float _X);
double __cdecl sqrt(double _X);
float __cdecl sqrtf(float _X);
int __cdecl strcmp(char *_Str1,char *_Str2);
void _guard_dispatch_icall(void);
void _guard_dispatch_icall(void);
void FUN_140079bc0(undefined8 param_1,longlong param_2);
void FUN_140079bf0(undefined8 param_1,longlong param_2);
void FUN_140079cc0(undefined8 param_1,longlong param_2);
void FUN_140079dbc(undefined8 param_1,longlong param_2);
void FUN_140079e0e(undefined8 param_1,longlong param_2);
void FUN_140079e90(undefined8 param_1,longlong param_2);
undefined8 FUN_140079ec0(void);
undefined8 FUN_140079ede(void);
void FUN_140079efc(undefined8 param_1,undefined8 *param_2);
void FUN_140079f6c(undefined8 param_1,longlong param_2);
undefined8 FUN_140079fbc(void);
undefined8 FUN_140079fda(void);
undefined8 FUN_140079ff8(undefined8 param_1,longlong param_2);
void FUN_14007a07c(undefined8 param_1,longlong param_2);
void FUN_14007a0cc(undefined8 param_1,longlong param_2);
undefined8 FUN_14007a116(undefined8 param_1,longlong param_2);
void FUN_14007a254(undefined8 param_1,longlong param_2);
void FUN_14007a2cd(undefined8 param_1,longlong param_2);
void FUN_14007a34e(undefined8 param_1,longlong param_2);
void FUN_14007a3e8(undefined8 param_1,longlong param_2);
void FUN_14007a47e(undefined8 param_1,longlong param_2);
void FUN_14007a4f3(undefined8 param_1,longlong param_2);
undefined8 FUN_14007a561(undefined8 param_1,longlong param_2,undefined8 param_3,undefined8 param_4);
void FUN_14007a5b0(undefined8 param_1,longlong param_2);
void FUN_14007a612(undefined8 param_1,longlong param_2);
void FUN_14007a697(undefined8 param_1,longlong param_2);
void FUN_14007a6c1(undefined8 param_1,longlong param_2);
void FUN_14007a730(undefined8 param_1,longlong param_2);
void FUN_14007a77c(undefined8 param_1,longlong param_2);
void FUN_14007a7b0(undefined8 param_1,longlong param_2);
void FUN_14007a7fc(undefined8 param_1,longlong param_2);
bool FUN_14007a914(undefined8 param_1,longlong param_2,undefined8 param_3,undefined8 param_4);
bool FUN_14007a990(undefined8 param_1,longlong param_2,undefined8 param_3,undefined8 param_4);
undefined8 FUN_14007aa14(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4);
void FUN_14007aa87(undefined8 param_1,longlong param_2);
void FUN_14007ab08(undefined8 param_1,longlong param_2);
void FUN_14007ab65(undefined8 param_1,longlong param_2);
void FUN_14007ad06(undefined8 param_1,longlong param_2);
void FUN_14007ad2f(undefined8 param_1,longlong param_2);
undefined8 FUN_14007aed8(undefined8 param_1,longlong param_2);
void FUN_14007afcd(undefined8 param_1,longlong param_2);
void FUN_14007b13a(undefined8 param_1,longlong param_2);
void FUN_14007b15a(undefined8 param_1,longlong param_2);
void FUN_14007b1e6(undefined8 param_1,longlong param_2);
void FUN_14007b220(undefined8 param_1,longlong param_2,undefined8 param_3,undefined8 param_4);
void FUN_14007b2ec(undefined8 param_1,longlong param_2);
undefined8 FUN_14007b391(undefined8 param_1,longlong param_2,undefined8 param_3,undefined8 param_4);
void FUN_14007b3c0(undefined8 param_1,longlong param_2);
undefined8 FUN_14007b430(void);
void FUN_14007b495(void);
void FUN_14007b500(undefined8 param_1,longlong param_2);
void FUN_14007b530(undefined8 param_1,longlong param_2);
void FUN_14007b570(undefined8 param_1,longlong param_2);
void FUN_14007b5c0(undefined8 param_1,longlong param_2);
void FUN_14007b678(undefined8 param_1,longlong param_2);
void FUN_14007b730(undefined8 param_1,longlong param_2);
void FUN_14007b760(undefined8 param_1,longlong param_2);
void FUN_14007b79c(undefined8 param_1,longlong param_2);
undefined8 FUN_14007b804(undefined8 param_1,longlong param_2);
undefined8 FUN_14007b864(undefined8 param_1,longlong param_2);
undefined8 FUN_14007b8b8(undefined8 param_1,longlong param_2);
undefined8 FUN_14007b918(undefined8 param_1,longlong param_2);
void FUN_14007b960(undefined8 param_1,longlong param_2);
undefined8 FUN_14007ba18(undefined8 param_1,longlong param_2);
void FUN_14007ba80(undefined8 param_1,longlong param_2);
undefined8 FUN_14007bb18(undefined8 param_1,longlong param_2);
void FUN_14007bba8(undefined8 param_1,longlong param_2);
void FUN_14007bc18(undefined8 param_1,longlong param_2);
void FUN_14007bc3e(undefined8 param_1,longlong param_2);
undefined8 FUN_14007bc88(undefined8 param_1,longlong param_2);
undefined8 FUN_14007bcca(undefined8 param_1,longlong param_2);
undefined8 FUN_14007bd0c(undefined8 param_1,longlong param_2);
void FUN_14007bdec(undefined8 param_1,longlong param_2);
void FUN_14007be12(undefined8 param_1,longlong param_2);
void FUN_14007be6c(undefined8 param_1,longlong param_2);
void FUN_14007beec(undefined8 param_1,longlong param_2);
void FUN_14007bf15(undefined8 param_1,longlong param_2);
void FUN_14007bf60(undefined8 param_1,longlong param_2);
void FUN_14007bfb8(undefined8 param_1,longlong param_2);
void FUN_14007bfe0(undefined8 param_1,longlong param_2);
void FUN_14007c034(undefined8 param_1,longlong param_2);
void FUN_14007c05d(undefined8 param_1,longlong param_2);
void FUN_14007c092(undefined8 param_1,longlong param_2);
void FUN_14007c14c(undefined8 param_1,longlong param_2);
void FUN_14007c1a5(undefined8 param_1,longlong param_2);
void FUN_14007c1ce(undefined8 param_1,longlong param_2);
void FUN_14007c21b(undefined8 param_1,longlong param_2);
void FUN_14007c250(undefined8 param_1,longlong param_2);
void FUN_14007c2cc(undefined8 param_1,longlong param_2);
undefined8 FUN_14007c318(undefined8 param_1,longlong param_2);
void FUN_14007c3a0(undefined8 param_1,longlong param_2);
void FUN_14007c3d0(undefined8 param_1,longlong param_2);
void FUN_14007c400(undefined8 param_1,longlong param_2);
void FUN_14007c5a0(undefined8 param_1,longlong param_2);
void FUN_14007c650(undefined8 param_1,longlong param_2);
void FUN_14007c6e0(undefined8 param_1,longlong param_2);
void FUN_14007caa7(void);
void FUN_14007cb20(void);
void FUN_14007cbc0(void);
void FUN_14007cc4c(undefined8 param_1,longlong param_2);
undefined4 FUN_14007cc78(undefined8 param_1,longlong param_2);
bool FUN_14007ccd7(undefined8 *param_1);
void FUN_14007ccef(undefined8 *param_1);
undefined8 FUN_14007cd0d(void);
void FUN_14007cd30(void);
void FUN_14007cd80(void);
void FUN_14007cdf0(void);
void FUN_14007ce70(void);
void FUN_14007cee0(void);
void FUN_14007cf90(void);
void __thiscall std::_Fac_tidy_reg_t::~_Fac_tidy_reg_t(_Fac_tidy_reg_t *this);

