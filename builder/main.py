# Copyright 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from platform import system
from os import makedirs
from os.path import isdir, join, isfile

from SCons.Script import (COMMAND_LINE_TARGETS, AlwaysBuild, Builder, Default,
                          DefaultEnvironment)

env = DefaultEnvironment()
platform = env.PioPlatform()

#overides the default upload.maximum_size value which is used to calculate how much of the memory is used up
if "size" in env.BoardConfig().get("build") and "application_type" in env.GetProjectOptions(as_dict=True):
        
    ApplicationType = env.GetProjectOptions(as_dict=True).get("application_type")
    ProgramSize = env.BoardConfig().get("build.size.full")

    if "boot" == ApplicationType:
        # use the bootloader linker
        ProgramSize = env.BoardConfig().get("build.size.boot")

    elif "app" == ApplicationType:
        ProgramSize = env.BoardConfig().get("build.size.app")

    env.BoardConfig().update("upload.maximum_size", ProgramSize);




env.Replace(
    AR="arm-none-eabi-ar",
    AS="arm-none-eabi-as",
    CC="arm-none-eabi-gcc",
    CXX="arm-none-eabi-g++",
    GDB="arm-none-eabi-gdb",
    OBJCOPY="arm-none-eabi-objcopy",
    OBJDUMP="arm-none-eabi-objdump",
    RANLIB="arm-none-eabi-ranlib",
    SIZETOOL="arm-none-eabi-size",

    ARFLAGS=["rc"],

    SIZEPROGREGEXP=r"^(?:\.text|\.data|\.rodata|\.text.align|\.ARM.exidx)\s+(\d+).*",
    SIZEDATAREGEXP=r"^(?:\.data|\.bss|\.noinit)\s+(\d+).*",
    SIZECHECKCMD="$SIZETOOL -A -d $SOURCES",
    SIZEPRINTCMD='$SIZETOOL -B -d $SOURCES',

    PROGSUFFIX=".elf"
)
# Allow user to override via pre:script
if env.get("PROGNAME", "program") == "program":
    env.Replace(PROGNAME="firmware")

env.Append(
    BUILDERS=dict(
        ElfToBin=Builder(
            action=env.VerboseAction(" ".join([
                "$OBJCOPY",
                "-O",
                "binary",
                "$SOURCES",
                "$TARGET"
            ]), "Bin Output -> $TARGET"),
            suffix=".bin"
        ),
        ElfToHex=Builder(
            action=env.VerboseAction(" ".join([
                "$OBJCOPY",
                "-O",
                "ihex",
                "-R",
                ".eeprom",
                "$SOURCES",
                "$TARGET"
            ]), "Hex Output -> $TARGET"),
            suffix=".hex"
        ),
        MergeHex=Builder(
            action=env.VerboseAction(" ".join([
                join(platform.get_package_dir("tool-sreccat") or "",
                     "srec_cat"),
                "$SOFTDEVICEHEX",
                "-intel",
                "$SOURCES",
                "-intel",
                "-o",
                "$TARGET",
                "-intel",
                "--line-length=44"
            ]), "Building $TARGET"),
            suffix=".hex"
        ),
        ObjectDump=Builder(
            action=env.VerboseAction(" ".join([
                "$OBJDUMP",
                "-D",
                "$SOURCES",
                ">",
                "$TARGET"
            ]), "disassembler Output -> $TARGET"),
            suffix=".dis"
        )
    )
)
if not env.get("PIOFRAMEWORK"):
    env.SConscript("frameworks/_bare.py")

#
# Target: Build executable and linkable firmware
#
target_firm_elf = None
target_firm_hex = None
object_dump_dis = None


if "nobuild" in COMMAND_LINE_TARGETS:
    target_firm_elf = join("$BUILD_DIR", "${PROGNAME}.elf")
    target_firm_hex = join("$BUILD_DIR", "${PROGNAME}.hex")
    target_firm = join("$BUILD_DIR", "${PROGNAME}.bin")
else:
    target_firm_elf = env.BuildProgram()
    
    if "SOFTDEVICEHEX" in env:
        merged_softdevice_hex = env.MergeHex(join("$BUILD_DIR", "${PROGNAME}"), env.ElfToHex(join("$BUILD_DIR", "user_${PROGNAME}"), target_firm_elf))
        target_firm_hex = join("$BUILD_DIR", "user_${PROGNAME}.hex")
    else :
        target_firm_hex = env.ElfToHex(join("$BUILD_DIR", "${PROGNAME}"), target_firm_elf)

    object_dump_dis = env.ObjectDump(join("$BUILD_DIR", "${PROGNAME}"), target_firm_elf)
    target_firm = env.ElfToBin(join("$BUILD_DIR", "${PROGNAME}"), target_firm_elf)


#
# Target: Upload by default .bin file
#
if env.subst("$UPLOAD_PROTOCOL") == "teensy-gui" and not isfile( join( platform.get_package_dir("tool-teensy") or "", "teensy_post_compile.exe" if system() == "Windows" else "teensy_post_compile") ):
    env.Replace(UPLOAD_PROTOCOL="teensy-cli")

upload_protocol = env.subst("$UPLOAD_PROTOCOL")
debug_tools = env.BoardConfig().get("debug.tools", {})
upload_source = target_firm

if upload_protocol.startswith("jlink"):

    def _jlink_cmd_script(env, source):
        build_dir = env.subst("$BUILD_DIR")
        if not isdir(build_dir):
            makedirs(build_dir)
        script_path = join(build_dir, "upload.jlink")
        commands = [
            "h",
            "loadbin %s, %s" % (source, env.BoardConfig().get(
                "upload.offset_address", "0x0")),
            "r",
            "q"
        ]
        with open(script_path, "w") as fp:
            fp.write("\n".join(commands))
        return script_path

    env.Replace(
        __jlink_cmd_script=_jlink_cmd_script,
        UPLOADER="JLink.exe" if system() == "Windows" else "JLinkExe",
        UPLOADERFLAGS=[
            "-device", env.BoardConfig().get("debug", {}).get("jlink_device"),
            "-speed", "4000",
            "-if", ("jtag" if upload_protocol == "jlink-jtag" else "swd"),
            "-autoconnect", "1"
        ],
        UPLOADCMD='$UPLOADER $UPLOADERFLAGS -CommanderScript "${__jlink_cmd_script(__env__, SOURCE)}"'
    )

    AlwaysBuild(env.Alias("upload", upload_source, [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]))
#elif upload_protocol in debug_tools:
#    env.Replace(
#        UPLOADER="openocd",
#        UPLOADERFLAGS=["-s", platform.get_package_dir("tool-openocd") or ""] +
#        debug_tools.get(upload_protocol).get("server").get("arguments", []) + [
#            "-c",
#            "program {$SOURCE} verify reset %s; shutdown;" %
#            env.BoardConfig().get("upload.offset_address", "")
#        ],
#        UPLOADCMD="$UPLOADER $UPLOADERFLAGS")
#
#    if not env.BoardConfig().get("upload").get("offset_address"):
#        upload_source = target_firm_elf
#
#    AlwaysBuild(env.Alias("upload", upload_source, [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]))
# custom upload tool
elif upload_protocol == "custom":
    AlwaysBuild(env.Alias("upload", upload_source, [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]))

elif upload_protocol == "nrfjprog":

    env.Replace(    ERASEFLAGS=["--eraseall", "-f", "NRF52"],
                    ERASECMD="nrfjprog_bin $ERASEFLAGS",
                    UPLOADER="nrfjprog_bin",
                    UPLOADERFLAGS=[
                        "--chiperase",
                        "--reset"
                    ],
                    PARTIAL_UPLOADERFLAGS=[
                        "--sectoranduicrerase",
                        "--reset"
                    ],
                    UPLOADCMD="$UPLOADER $UPLOADERFLAGS --program $SOURCE",
                    PARTIAL_UPLOADCMD="$UPLOADER $PARTIAL_UPLOADERFLAGS --program $SOURCE")
    AlwaysBuild(env.Alias("erase", None, env.VerboseAction("$ERASECMD", "Erasing...")))

    if merged_softdevice_hex :
        AlwaysBuild(env.Alias("upload_softdevice", env.get('SOFTDEVICEHEX'), [env.VerboseAction("$PARTIAL_UPLOADCMD", "Uploading $SOURCE")]))
        AlwaysBuild(env.Alias("upload", target_firm_hex, [env.VerboseAction("$PARTIAL_UPLOADCMD", "Uploading $SOURCE")]))
        AlwaysBuild(env.Alias("upload_merged", merged_softdevice_hex, [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]))
    else :
        AlwaysBuild(env.Alias("upload", target_firm_hex, [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]))

elif upload_protocol == "teensy-cli":
    env.Replace(
        REBOOTER="teensy_reboot",
        UPLOADER="teensy_loader_cli",
        UPLOADERFLAGS=[
            "-mmcu=$BOARD_MCU",
            "-w",  # wait for device to appear
            "-s",  # soft reboot if device not online
            "-v"  # verbose output
        ],
        UPLOADCMD="$UPLOADER $UPLOADERFLAGS $SOURCES"
    )

    AlwaysBuild(env.Alias("upload", target_firm_hex, [ env.VerboseAction("$REBOOTER -s", "Rebooting..."), env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE") ]))

elif upload_protocol == "teensy-gui":
    env.Replace(
        UPLOADER="teensy_post_compile",
        UPLOADERFLAGS=[
            "-file=${PROGNAME}", '-path="$BUILD_DIR"',
            "-tools=%s" % (platform.get_package_dir("tool-teensy") or ""),
            "-board=%s" % env.BoardConfig().id.upper(),
            "-reboot"
        ],
        UPLOADCMD="$UPLOADER $UPLOADERFLAGS"
    )

    AlwaysBuild(env.Alias("upload", target_firm_hex, [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]))
else:
    sys.stderr.write("Warning! Unknown upload protocol %s\n" % upload_protocol)


AlwaysBuild(env.Alias("nobuild", target_firm))

#target_buildprog = env.Alias("buildprog", target_firm)
#
# Target: Print binary size
#

target_size = env.Alias("size", target_firm_elf, env.VerboseAction("$SIZEPRINTCMD", "Calculating size $SOURCE"))
AlwaysBuild(target_size)

#
# Default targets
#
Default([
        env.Alias("buildprog", target_firm),
        env.Alias("hex", target_firm_hex),
        env.Alias("dumpDis", object_dump_dis),
        target_size
        ])