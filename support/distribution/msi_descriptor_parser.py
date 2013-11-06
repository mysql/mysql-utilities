#
# Copyright (c) 2013 Oracle and/or its affiliates. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#

from xml.dom.minidom import parse, parseString
import os

# MySQL Utilities\scripts\etc\mysql\fabric.cfg
dir_fab_conf = ('<Directory>'
    '<Directory Id="Scripts" Name="scripts">'
    '<Directory Id="ETC" Name="etc">'
    '<Directory Id="FABCONF" Name="mysql"/>'
    '</Directory>'
    '</Directory>'
    '</Directory>'
)

file_exe_fab = ('<Component>'
    '<File Id="exe_mysqlfabric" Name="mysqlfabric.exe"'
    ' Source="$(var.BuildDir)\\mysqlfabric.exe" DiskId="1"/>'
    '</Component>'
)

dirref_fab =('<Product>'
    '<DirectoryRef Id="FABCONF">'
    '<Component Id="Fabric_config"'
    ' Guid="CA95B0AF-5500-48CD-9707-56608AE78491">'
    '<RemoveFolder Id="RemScripts" Directory="Scripts" On="uninstall"/>'
    '<RemoveFolder Id="RemMySQLDir" Directory="ETC" On="uninstall"/>'
    '<RemoveFolder Id="RemFABCONF" Directory="FABCONF" On="uninstall"/>'
    '<RegistryKey Root="HKCU"'
    ' Key="Software\\MySQL\\MySQL Utilities\\fabric"'
    ' Action="createAndRemoveOnUninstall">'
    '<RegistryValue Type="string" Name="Location" Value="[FABCONF]"/>'
    '</RegistryKey>'
    '<RegistryKey Root="HKCU"'
    ' Key="Software\\MySQL AB\\MySQL Utilities\\fabric"'
    ' Action="createAndRemoveOnUninstall">'
    '<RegistryValue Type="string" Name="Location" Value="[FABCONF]"/>'
    '</RegistryKey>'
    '<File Id="main.cfg"'
    ' Source="$(var.BuildDir)\\scripts\\etc\\mysql\\fabric.cfg"'
    ' Checksum="yes"/>'
    '</Component>'
    '</DirectoryRef>'
    '</Product>'
)

compref_fab = ('<Feature>'
    '<ComponentRef Id="Fabric_config"/>'
    '</Feature>'
)

dir_php_zip = ('<Directory>'
    '<Directory Id="DOCTRINEZIP" Name="Doctrine extensions for PHP"/>'
    '</Directory>'
)

comp_doczip_menu = ('<Component>'
    '<Shortcut Description="[DOCTRINEZIP]" Id="zip_doczip" '
    'Name="Doctrine extensions for PHP" '
    'Target="[INSTALLDIR]Doctrine extensions for PHP"/>'
    '</Component>'
)

dirref_doczip = ('<Product><DirectoryRef Id="DOCTRINEZIP">'
    '<Component Guid="cadd4711-6c3d-426f-a646-ad4f3a62f885" Id="SetupRegistryDocZip">'
    '<RegistryKey Action="createAndRemoveOnUninstall" Key="Software\MySQL\MySQL Utilities\[DOCTRINEZIP]" Root="HKCU">'
    '<RegistryValue KeyPath="yes" Name="Version" Type="string" Value="$(var.Version)"/>'
    '<RegistryValue Name="Location" Type="string" Value="[DOCTRINEZIP]"/>'
    '</RegistryKey>'
    '<RegistryKey Action="createAndRemoveOnUninstall" Key="Software\MySQL AB\MySQL Utilities\[DOCTRINEZIP]" Root="HKCU">'
    '<RegistryValue Name="Version" Type="string" Value="$(var.Version)"/>'
    '<RegistryValue Name="Location" Type="string" Value="[DOCTRINEZIP]"/>'
    '</RegistryKey>'
    '</Component>'
    '<Component Guid="78e37230-fc92-43f3-aad2-5920d228cee0" Id="SetupEnvDocZip">'
    '<CreateFolder/>'
    '<Environment Action="set" Id="SystemPathDocZip" Name="PATH" Part="last" Permanent="no" System="yes" Value="[DOCTRINEZIP]"/>'
    '</Component>'
    '<Component Guid="d8069f9b-5d6b-4643-9273-78e2ab016edd" Id="DocZip">'
    '<File Checksum="yes" Id="{docphp_id}" Source="$(var.BuildDir)\\scripts\\etc\\mysql\\{docphp}"/>'
    '</Component>'
    '</DirectoryRef></Product>'
)

dir_docphp = '<Directory Id="DocMenu" Name="Documentation"/>'

compref_doczip = ('<Feature>'
    '<ComponentRef Id="SetupRegistryDocZip"/>'
    '<ComponentRef Id="SetupEnvDocZip"/>'
    '<ComponentRef Id="DocZip"/>'
    '</Feature>'
)


def append_childs_from_unparsed_xml(fatherNode, unparsed_xml):
    dom3 = parseString(unparsed_xml)
    childNodes = dom3.firstChild.childNodes
    for child_index in range(len(childNodes)):
        childNode = childNodes.item(0)
        fatherNode.appendChild(childNode)


def get_element(dom_msi, tagName, name=None, id=None):
    product = dom_msi.getElementsByTagName("Product")[0]
    elements = product.getElementsByTagName(tagName)
    for element in elements:
        if name and id:
            if (element.getAttribute('Name') == name and
                element.getAttribute('Id') == id):
                return element
        elif id:
            if element.getAttribute('Id') == id:
                return element


def add_fabric_elements(dom_msi):
    # Define the Directories structure that will be used on the installation 
    # to Directory.
    dir_in = get_element(dom_msi, "Directory", name='MySQL Utilities',
                         id="INSTALLDIR")
    append_childs_from_unparsed_xml(dir_in, dir_fab_conf)

    # Add the Fabric scripts.
    diref = get_element(dom_msi, "DirectoryRef", id='INSTALLDIR')
    comps = diref.getElementsByTagName('Component')
    for com in comps:
        if com.getAttribute('Id') == 'UtilsExe':
            append_childs_from_unparsed_xml(com, file_exe_fab)

    # Define the files to be installed on DirectoryRef.
    product = dom_msi.getElementsByTagName("Product")[0]
    append_childs_from_unparsed_xml(product, dirref_fab)

    # Set ComponentRef to Feature, that list elements to be installed 
    # We need to include the references to all elements added before. 
    feature = get_element(dom_msi, "Feature", id="Install")
    append_childs_from_unparsed_xml(feature, compref_fab)


def add_doczip_elements(dom_msi, doc_zip_ver):
    # Get the Directory elements, that is where the installation 
    # directory structure is defined.
    dir = get_element(dom_msi, "Directory", name='MySQL Utilities', id="INSTALLDIR")
    append_childs_from_unparsed_xml(dir, dir_php_zip)

    # Add Doctrine folder and files
    product = dom_msi.getElementsByTagName("Product")[0]
    dirref = dirref_doczip.format(docphp_id=doc_zip_ver.replace('-', '_'),
                                  docphp=doc_zip_ver)
    append_childs_from_unparsed_xml(product, dirref)

    # Add Doctrine shortcut.
    diref = get_element(dom_msi, "DirectoryRef", id="UtilsMenu")
    comps = diref.getElementsByTagName('Component')
    for com in comps:
        if com.getAttribute('Id') == 'UtilsShortcuts':
            append_childs_from_unparsed_xml(com, comp_doczip_menu)

    # Set ComponentRef to Feature, that list elements to be installed 
    # We need to include the references to all elements added before. 
    feature = get_element(dom_msi, "Feature", id="Install")
    append_childs_from_unparsed_xml(feature, compref_doczip)


def _print(log, msg):
    if log:
        log.info(msg)
    print(msg)

def add_features(xml_path, result_path, add_fabric=False, add_doczip=False,
                 log=None):
    """Adds the nessesary entries to the msi build descriptor to include 
       Fabric and Doctrine.

       xml_path[in]       The original xml msi descriptor path
       result_path[in]    Path to save the resulting xml
       add_fabric[in]     If True, fabric information will be added
       add_doczip[in]     If True, Doctrine information will be added
       log[in]            build command log instance
    """
    dom_msi = parse(xml_path)
    if add_fabric:
        add_fabric_elements(dom_msi)
    if add_doczip:
        add_doczip_elements(dom_msi, add_doczip)
    _print(log, "Saving xml to:{0} working directory:{1}"
           "".format(result_path, os.getcwd()))
    f = open(result_path, "w+")
    f.write(dom_msi.toprettyxml())
    f.flush()
    f.close()

