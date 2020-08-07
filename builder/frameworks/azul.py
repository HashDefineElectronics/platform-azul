from os.path import isfile, isdir, join
from SCons.Script import DefaultEnvironment


env = DefaultEnvironment()
platform = env.PioPlatform()

FRAMEWORK_DIR = platform.get_package_dir("framework-azul")

#
# get the compiler optimizer value. for possible values see https://gcc.gnu.org/onlinedocs/gcc-4.4.7/gcc/Optimize-Options.html
#
def getOptimizeFlag() :

    Result = env.BoardConfig().get("build").get("optimize_flag")

    if not Result :
        Result = "-Os"
    return Result

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

    AdditionPath = env.BoardConfig().get("build").get("includeheaderPaths")
    if isinstance(AdditionPath, list) :
        for Item in AdditionPath:
            Path = join(FRAMEWORK_DIR, env.BoardConfig().get("build.device"), Item)
            if isdir(Path) :
                TempPath.append(Path)

    return TempPath

#
# This function is a wrapper for adding Source files into LIBS
#
def addSourceFileToLib(libs) :

    StartupPath = join(FRAMEWORK_DIR, env.BoardConfig().get("build.device"), "Source")

    FullStartFilePath = join(StartupPath, "gcc", env.BoardConfig().get("build.startup_file"))
    
    assert isfile(FullStartFilePath), FullStartFilePath + ' - startup_file not found.'

    AdditionSourceFiles = env.BoardConfig().get("build").get("IncludeSource")

    SourFilter = ""

    if isinstance(AdditionSourceFiles, list):
        for Item in AdditionSourceFiles:
            Temp = join(FRAMEWORK_DIR, env.BoardConfig().get("build.device"), Item)
            if isfile(Temp):
                SourFilter += " +<%s>" % (Temp)
    
    if SourFilter is "":
        SourFilter = "+<*.c>"

    SourFilter = "-<*> %s +<gcc/%s>" % (SourFilter, env.BoardConfig().get("build.startup_file"))

    # include the .c startup and .S assembler
    libs.append( env.BuildLibrary(join("$BUILD_DIR"), StartupPath, src_filter=SourFilter) )

env.Append(
    ASFLAGS=["-x", "assembler-with-cpp"],
    CCFLAGS=[
        getOptimizeFlag(),  # optimize for size
        "-ffunction-sections",  # place each function in its own section
        "-fdata-sections",
        "-mthumb",
        "-nostdlib",
        "-Wl,-map"
    ],

    CXXFLAGS=[
        "-fno-rtti",
        "-fno-exceptions"
    ],

    CPPDEFINES=[
        ("F_CPU", "$BOARD_F_CPU")
    ],

    LINKFLAGS=[
        getOptimizeFlag(),
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
            "-L%s" % join(FRAMEWORK_DIR, env.BoardConfig().get("build.device"), "Source/gcc/linker"),
            "-mcpu=%s" % env.BoardConfig().get("build.cpu")
        ]
    )

if env.BoardConfig().get("build").get("compiler_flags"):
    CCFLAGS = env.BoardConfig().get("build").get("compiler_flags").get("CCFLAGS")
    if(isinstance(CCFLAGS, list)) :
        env.Append(CCFLAGS=CCFLAGS)

    LINKFLAGS = env.BoardConfig().get("build").get("compiler_flags").get("LINKFLAGS")
    if(isinstance(LINKFLAGS, list)) :
        env.Append(LINKFLAGS=LINKFLAGS)

# copy CCFLAGS to ASFLAGS (-x assembler-with-cpp mode)
env.Append(ASFLAGS=env.get("CCFLAGS", [])[:])

# Use our own linker
env.Replace(
    LDSCRIPT_PATH=env.subst(getLinker())
)

print(env.get('LINKFLAGS'))

SoftDevicePath = env.BoardConfig().get("build").get('softdevice_path')
if SoftDevicePath :
    softdevice_hex_path = join(env.get("PROJECTSRC_DIR"), "../", SoftDevicePath)
    
    if softdevice_hex_path and isfile(softdevice_hex_path):
        env.Append(SOFTDEVICEHEX=softdevice_hex_path)
    else:
        print("Warning! softdevice not found " + softdevice_hex_path)