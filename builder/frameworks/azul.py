from os.path import isfile, join
from SCons.Script import DefaultEnvironment


env = DefaultEnvironment()
platform = env.PioPlatform()

FRAMEWORK_DIR = platform.get_package_dir("framework-azul")

#
# Get the linker script
#
def getLinker() :

    ldscript = join(FRAMEWORK_DIR, env.BoardConfig().get("build.device"), "Source", "gcc", "linker", env.BoardConfig().get("build.linker_file"))
    assert isfile(ldscript), ldscript + " - linker_file not found."
    return ldscript
    
#
# Hanlde adding addition header search path to our built system
#
def getHeaderPath() :

    TempPath = [join(FRAMEWORK_DIR, env.BoardConfig().get("build.device"), "Include"),
                join(FRAMEWORK_DIR, env.BoardConfig().get("build.device"), "Include", "CMSIS")]
    return TempPath

#
# This function is a wrapper for adding Source files into LIBS
#
def addSourceFileToLib(libs) :

    StartupPath = join(FRAMEWORK_DIR, env.BoardConfig().get("build.device"), "Source")
    FullStartFilePath = join(StartupPath, "gcc", env.BoardConfig().get("build.startup_file"))
    
    assert isfile(FullStartFilePath), FullStartFilePath + ' - startup_file not found.'

    # include the .c startup and .S assembler
    libs.append(env.BuildLibrary(join("$BUILD_DIR"), StartupPath, src_filter="-<*> +<*.c> +<gcc/" + env.BoardConfig().get("build.startup_file") + ">"))
    


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
    CPPPATH=getHeaderPath(),
    LIBS=["c", "gcc", "m", "stdc++", "nosys"]
)

libs = []
addSourceFileToLib(libs)
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
env.Replace(
    LDSCRIPT_PATH=env.subst(getLinker())
)

#print('__________________________')
#print(env.Dump())
#print('__________________________')