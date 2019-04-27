from os.path import isfile, join
from SCons.Script import DefaultEnvironment


env = DefaultEnvironment()
platform = env.PioPlatform()

FRAMEWORK_DIR = platform.get_package_dir("framework-azul")

#
# Get the linker script
#
def getLinker(buildConfig) :
    
    ldscript = join(FRAMEWORK_DIR, buildConfig.device, "Source", "gcc", "linker", buildConfig.linker_file)
    assert isfile(ldscript)
    return ldscript
    
#
# Hanlde adding addition header search path to our built system
#
def getHeaderPath(buildConfig) :

    TempPath = [join(FRAMEWORK_DIR, buildConfig.device, "Include")]
    return TempPath

#
# This function is a wrapper for adding Source files into LIBS
#
def addSourceFileToLib(buildConfig, libs) :

    StartupPath = join(FRAMEWORK_DIR, buildConfig.device, "Source")

    # include the .c startup and .S assembler
    libs.append(env.BuildLibrary(join("$BUILD_DIR"), StartupPath, src_filter="-<*> +<*.c> +<**/" + buildConfig.startup_file + ">"))


env.Append(
    ASFLAGS=["-x", "assembler-with-cpp"],
    CCFLAGS=[
        "-Os",  # optimize for size
        "-ffunction-sections",  # place each function in its own section
        "-fdata-sections",
        "-Wall",
        "-mthumb",
        "-nostdlib"
    ],

    CXXFLAGS=[
        "-fno-rtti",
        "-fno-exceptions"
    ],

    CPPDEFINES=[
        ("F_CPU", "$BOARD_F_CPU")
    ],

    LINKFLAGS=[
        "-Os",
        "-Wl,--gc-sections,--relax",
        "-mthumb",
        "--specs=nano.specs",
        "--specs=nosys.specs"
    ],
    CPPPATH=getHeaderPath(env.BoardConfig().get("build")),
    LIBS=["c", "gcc", "m", "stdc++", "nosys"]
)

libs = []
addSourceFileToLib(env.BoardConfig().get("build"), libs)
env.Append(LIBS=libs)

if "BOARD" in env:
    env.Append(
        CCFLAGS=[
            "-mcpu=%s" % env.BoardConfig().get("build.cpu")
        ],
        LINKFLAGS=[
            "-mcpu=%s" % env.BoardConfig().get("build.cpu")
        ]
    )
# copy CCFLAGS to ASFLAGS (-x assembler-with-cpp mode)
env.Append(ASFLAGS=env.get("CCFLAGS", [])[:])

# Use our own linker
env.Replace(LDSCRIPT_PATH=env.subst(getLinker(env.BoardConfig().get("build"))))

#print('__________________________')
#print(env.Dump())
#print('__________________________')