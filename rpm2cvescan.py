#!/usr/bin/python
import rpm

namespace='{http://oval.mitre.org/XMLSchema/oval-definitions-5}'
patchlist = []
rhelversions = ['RHEL5', 'RHEL6', 'RHEL7', 'RHEL8' ]
base_patchfilename='./com.redhat.rhsa-'

# =======================================================================
# Monkey patch ElementTree
import xml.etree.ElementTree as ET

# Function to import xml in the order it's stored in the xml
# instead of just random dump items in dict
def _serialize_xml(write, elem, encoding, qnames, namespaces):
    tag = elem.tag
    text = elem.text
    if tag is ET.Comment:
        write("<!--%s-->" % ET._encode(text, encoding))
    elif tag is ET.ProcessingInstruction:
        write("<?%s?>" % ET._encode(text, encoding))
    else:
        tag = qnames[tag]
        if tag is None:
            if text:
                write(ET._escape_cdata(text, encoding))
            for e in elem:
                _serialize_xml(write, e, encoding, qnames, None)
        else:
            write("<" + tag)
            items = elem.items()
            if items or namespaces:
                if namespaces:
                    for v, k in sorted(namespaces.items(),
                                       key=lambda x: x[1]):  # sort on prefix
                        if k:
                            k = ":" + k
                        write(" xmlns%s=\"%s\"" % (
                            k.encode(encoding),
                            ET._escape_attrib(v, encoding)
                            ))
                #for k, v in sorted(items):  # lexical order
                for k, v in items: # Monkey patch
                    if isinstance(k, ET.QName):
                        k = k.text
                    if isinstance(v, ET.QName):
                        v = qnames[v.text]
                    else:
                        v = ET._escape_attrib(v, encoding)
                    write(" %s=\"%s\"" % (qnames[k], v))
            if text or len(elem):
                write(">")
                if text:
                    write(ET._escape_cdata(text, encoding))
                for e in elem:
                    _serialize_xml(write, e, encoding, qnames, None)
                write("</" + tag + ">")
            else:
                write(" />")
    if elem.tail:
        write(ET._escape_cdata(elem.tail, encoding))

ET._serialize_xml = _serialize_xml

from collections import OrderedDict

class OrderedXMLTreeBuilder(ET.XMLTreeBuilder):
    def _start_list(self, tag, attrib_in):
        fixname = self._fixname
        tag = fixname(tag)
        attrib = OrderedDict()
        if attrib_in:
            for i in range(0, len(attrib_in), 2):
                attrib[fixname(attrib_in[i])] = self._fixtext(attrib_in[i+1])
        return self._target.start(tag, attrib)

# =======================================================================


# =======================================================================
# Class my_rpm
#
# Created to easily store rpm info and compare rpm versions
# =======================================================================
class my_rpm:
    def __init__(self, name_string):
	if ':' in name_string:
           self.name = name_string.split(':')[0].rsplit('-',1)[0]
        else:
           self.name = name_string.split('.')[0].rsplit('-',1)[0]

        self.version_string = name_string.strip(self.name+'-')

        if 'el' in self.version_string:
           self.rhversion = self.version_string.split('el')[1].split('.')[0]
        else:
           self.rhversion = 7

    def __eq__(self, other):
        """Override the default Equals behavior"""
        if isinstance(other, self.__class__):
           if self.name == other.name:
              result = rpm.labelCompare((self.epoch(), self.version(), self.release()), (other.epoch(), other.version(), other.release()))
              if result == 0:
                 return True
              else:
                 return False
           else:
              return False
        else:
           return NotImplemented

    def __ne__(self, other):
        """Override the default Not Equal behavior"""
        if isinstance(other, self.__class__):
           if self.name == other.name:
              result = rpm.labelCompare((self.epoch(), self.version(), self.release()), (other.epoch(), other.version(), other.release()))
              if result == 0:
                 return False
              else:
                 return True
           else:
              return True
        else:
           return NotImplemented

    def __ge__(self, other):
        """Override the default Greater or equal behavior"""
        if isinstance(other, self.__class__):
           if self.name == other.name:
              result = rpm.labelCompare((self.epoch(), self.version(), self.release()), (other.epoch(), other.version(), other.release()))
              if result >= 0:
                 return True
              else:
                 return False
           else:
              return False
        else:
           return NotImplemented

    def epoch(self):
        if ':' in self.version_string:
           return self.version_string.split(':')[0]
        else:
           return 0

    def version(self):
        if ':' in self.version_string:
           ver_string = self.version_string.split(':')[1]
        else:
           ver_string = self.version_string
        return ver_string.split('-')[0]

    def release(self):
        return ver_string.split('-')[1]

# =======================================================================

class my_patch:
    def __init__(self, name, version):
        self.name = name
        self.version = int(version)
        self.rhalist = []
        self.cvelist = []
        self.rpmlist = []

# =======================================================================
# Class my_cve
#
# Created to easily store cve info
# =======================================================================
class my_cve:
    def __init__(self, name, cvss, score):
        self.name = name
        self.cvss = int(cvss)
        self.score = float(score)

    #@classmethod
    def rating(self):
        if self.cvss == 3:
           if self.score > 8.9:
              severity = 'Critical'
           elif self.score > 6.9:
              severity = 'High'
           elif self.score > 3.9:
              severity = 'Medium'
           elif self.score > 0:
              severity = 'Low'
           else:
              severity = 'None'
        elif self.cvss == 2:
           if self.score > 6.9:
              severity = 'High'
           elif self.score > 3.9:
              severity = 'Medium'
           else:
              severity = 'Low'
        else:
           severity = 'Unknown'

        return severity

# =======================================================================


# =======================================================================
# Recursive criteria processing
#
# This is needed as RH CVE xml file is inconsistent with the amount
# of levels it uses for patch criteria
# =======================================================================
def recurse_criteria(my_criterion):
    my_rpmlist = []

    if my_criterion.tag == namespace+'criteria':
       for my_criteria in my_criterion:
           my_rpmlist += recurse_criteria(my_criteria)
    elif my_criterion.tag == namespace+'criterion':
       if 'is earlier than' in my_criterion.attrib['comment']:
          comment = my_criterion.attrib['comment'].split()
          rpmname_version = comment[0]+'-'+comment[-1]
          my_rpmlist.append(my_rpm(rpmname_version))

    return my_rpmlist

# =======================================================================

# get_patchlist
def get_patchlist(my_rhelversion):
    
    my_filename = base_patchfilename+my_rhelversion+'.xml'
    xml_tree = ET.parse(my_filename)

    my_patchlist = []
    #print xml_tree

    oval_definitions = xml_tree.getroot()
    for oval_subset in oval_definitions:
        #print (oval_subset.tag, "->", oval_subset.__dict__)

        if oval_subset.tag == namespace+'definitions':
           for oval_definition in oval_subset:

               #print oval_definition.tag, "-> ", oval_definition.__dict__
               patch_definition = oval_definition.attrib

               this_patch = my_patch(patch_definition['id'], patch_definition['version'])

               for patch_data in oval_definition:
                   #print patch_data.tag, "-> ", patch_data.__dict__
                   # Get CVE ID
                   if patch_data.tag == namespace+'metadata':
                      for metadata_data in patch_data:
                          if metadata_data.tag.endswith('reference'):
                             #print ""
                             #print metadata.__dict__
                             #print ""
                             if metadata_data.attrib['source'] != 'CVE':
                                this_patch.rhalist.append(metadata_data.attrib['ref_id'])

                      # get CVSS score of the CVE with this patch
                      if metadata_data.tag == namespace+'advisory':
                         for advisory_data in metadata_data:
                             # Assumption: CVSS3 score takes president over CVSS2
                             if 'cvss3' in advisory_data.keys():
                                cve = advisory_data.attrib['href'].split('/')[-1]
                                score_txt = advisory_data.attrib['cvss3'].split('/')[0]
                                score = float(score_txt)

                                this_patch.cvelist.append(my_cve(cve, 3, score))

                             elif 'cvss2' in advisory_data.keys():
                                cve = advisory_data.attrib['href'].split('/')[-1]
                                score_txt = advisory_data.attrib['cvss2'].split('/')[0]
                                score = float(score_txt)

                                this_patch.cvelist.append(my_cve(cve, 2, score))

                   # Weed trough criteria.
                   # At 1st level we always have criteria
                   # At 2nd and later levels it is possible to find a criterion
                   # with package name and version we need to store
                   if patch_data.tag == namespace+'criteria':
                      for criteria2 in patch_data:
                          this_patch.rpmlist += recurse_criteria(criteria2)

               my_patchlist.append(this_patch)
               del this_patch

    return my_patchlist

# =======================================================================

# get_patchlist
def print_patchlist(my_patchlist):
    
    for patch in my_patchlist:
        print patch.name, patch.version

        for rha in patch.rhalist:
            print '  {}'.format(rha)

        for cve in patch.cvelist:
            print ' ', cve.name, \
                  '-', cve.score, \
                  '-', cve.rating(), \
                  '(cvss{})'.format(cve.cvss)

        for rpm in patch.rpmlist:
            print '   ', rpm.name, \
                  '<', rpm.version_string, \
                  '({})'.format(rpm.rhversion)

        print ''
# =======================================================================

for rhelversion in rhelversions:
    patchlist = get_patchlist(rhelversion)
    print_patchlist(patchlist)

# get rpm list via command:
# rpm -qa --queryformat "%{NAME}-%{EPOCH}:%{VERSION}-%{RELEASE}\n" | sed 's/(none)/0/'
