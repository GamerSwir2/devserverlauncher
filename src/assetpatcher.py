# The following copyright notice applies to the Mono.Cecil library:

# Copyright (c) 2008 - 2015 Jb Evain
# Copyright (c) 2008 - 2011 Novell, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import clr
import sys
import os
import util
import io


#cecil_folder = os.path.abspath("./cecil")
#if cecil_folder not in sys.path:
#    sys.path.append(cecil_folder)

clr.AddReference(util.resource_path("Mono.Cecil"))
import Mono.Cecil as Cecil

clr.AddReference("System.Drawing")
from System.Drawing import Bitmap
from System.IO import File, MemoryStream
from System.Resources import ResourceReader, ResourceWriter

def patch_assets(target_dll, asset_array, asset_src_folder, output_path, resources_blob_name="osu_ui.ResourcesStore.resources"):
    reader_params = Cecil.ReaderParameters(Cecil.ReadingMode.Immediate)
    assembly = Cecil.AssemblyDefinition.ReadAssembly(target_dll, reader_params)
    module = assembly.MainModule

    target_resource = next((res for res in module.Resources if res.Name == resources_blob_name), None)
    if target_resource is None:
        raise Exception(f"Could not locate resource: {resources_blob_name}")

    original_resource_data = target_resource.GetResourceData()
    resource_entries = {}

    ms_in = MemoryStream(original_resource_data)
    reader = ResourceReader(ms_in)
    try:
        for entry in reader:
            resource_entries[entry.Key] = entry.Value
    finally:
        reader.Close()
        ms_in.Close()
        ms_in.Dispose()

    for asset_file in asset_array:
        asset_path = os.path.join(asset_src_folder, asset_file + ".png")
        if not os.path.exists(asset_path):
            print(f"Error: Missing file {asset_path}")
            continue

        with open(asset_path, "rb") as f:
            img_bytes = f.read()

        ms_img = MemoryStream(img_bytes)
        try:
            bitmap = Bitmap(ms_img)
            if asset_file in resource_entries:
                resource_entries[asset_file] = bitmap
                print(f"Replaced resource entry for: {asset_file}")
            else:
                print(f"Resource key '{asset_file}' not found in {resources_blob_name}.")
        finally:
            ms_img.Close()
            ms_img.Dispose()

    ms_out = MemoryStream()
    writer = ResourceWriter(ms_out)
    try:
        for key, val in resource_entries.items():
            writer.AddResource(key, val)
        writer.Generate()
        ms_out.Position = 0
        new_resources_data = ms_out.ToArray()
    finally:
        writer.Close()
        ms_out.Close()
        ms_out.Dispose()

    new_resource = Cecil.EmbeddedResource(
        target_resource.Name,
        target_resource.Attributes,
        new_resources_data
    )
    module.Resources.Remove(target_resource)
    module.Resources.Add(new_resource)

    assembly.Write(output_path)
    assembly.Dispose()
    print(f"Patched DLL written to {output_path}")
    return

if __name__ == "__main__":
    rtarget_dll = os.path.abspath("osu!ui.dll")
    routput_path = os.path.abspath("osu!uiPATCHED.dll")
    rasset_array = ["menu-osu@2x", "menu-osu"]
    rasset_src_folder = os.path.abspath("./assets")
    rresources_blob_name = "osu_ui.ResourcesStore.resources"

    try:
        os.remove(routput_path)
    except:
        pass

    patch_assets(
        target_dll=rtarget_dll,
        asset_array=rasset_array,
        asset_src_folder=rasset_src_folder,
        output_path=routput_path,
        resources_blob_name=rresources_blob_name
    )
