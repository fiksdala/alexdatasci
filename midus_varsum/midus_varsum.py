import pandas as pd
import numpy as np
import textract
from urllib.request import urlopen
import xml.etree.ElementTree as ET

tpath = '/Users/alex/Documents/alexdatasci/data_files/MIDUS_1/ICPSR_02760/DS0001/' \
    + '02760-0001-Documentation-scales.pdf'

# Extract text 
vartext = textract.process(tpath)
vartext = vartext.splitlines()
vartext = pd.Series(vartext)
vartext = vartext.str.decode('utf-8').str.strip()
vartext.replace('',np.nan,inplace=True)
vartext.dropna(inplace=True)
vartext.reset_index(drop=True,inplace=True)

# Drop preamble
vartext = vartext[177:].reset_index(drop=True)

# Extract relevant information: headings, scale names, scaleprefix

# Scale prefix
scaleprefix = pd.Series([1 if ']:' in i 
                         or (str(i).endswith(']') 
                             and '-' not in str(i) 
                             and not str(i).startswith(':')
                            )
                         else 0 for i in vartext])

# Scale names take a few forms:
#    Line prior to "[VARNAME]: (cont", 
scalefilt1 = pd.Series([1 if str(i).split('[')[0] == ''
                           and ']: (cont' in i else 0 
                           for i in vartext]).iloc[1:]
scalefilt1 = scalefilt1.append(pd.Series([0]),ignore_index=True)

#    Name prior to "[VARNAME]:BLANK": This is captured
#    in a different scaleprefix

#    Line prior to 'Items:' and Name prior to ':BLANK'
tempfilt = [True if i.split(':')[0]=='Items' else False for i in vartext]
tempfilt = pd.Series(tempfilt[1:]).append(pd.Series([0]), ignore_index=True)
scalefilt2 = np.array([False]).repeat(len(vartext))
for i in range(1,len(vartext)):
    if tempfilt[i]==1 and "]:" not in vartext[i]:
        scalefilt2[i]=True
    else:
        scalefilt2[i]=False

# Scale headings
scaleheading = pd.Series([1 if str(i).split(' (')[0].isupper()
                          and '[' not in i 
                          and i != 'AND' 
                          and '(' not in str(i).split(' (')[0]
                          and len(i) < 50
                          else 0 for i in vartext])

# Filter out extraneous text
vartext = vartext[(scaleprefix+scalefilt1+scalefilt2+scaleheading)>0]

# Some scale names are on a separate line, others are
# listed before the varname.
# First, drop text after "[VAR]:"
vartext = pd.Series([i[0] for i in vartext.str.split(':')])

# Then split examples with "Scale_name [VARNAME]" and flatten
vartext = pd.Series([i for j in vartext.str.split('[') for i in j])
# Drop ''
vartext = vartext[vartext!=''].reset_index(drop=True)

# Make series for heading, scale, and varnames
heading = np.array([None]).repeat(len(vartext))
heading[0] = vartext[0]
for i in range(1,len(vartext)):
    if vartext[i].split('(')[0].isupper() \
        and ']' not in vartext[i]:
        heading[i]=vartext[i]
    else:
        heading[i]=heading[i-1]

scale = np.array([None]).repeat(len(vartext))
scale[0] = None
for i in range(1,len(vartext)):
    if vartext[i].split('(')[0].isupper() \
        and ']' not in vartext[i]:
        scale[i]=None
    elif vartext[i].isupper()==False \
        and vartext[i].islower()==False:
        scale[i]=vartext[i]
    elif vartext[i].isupper() \
        and ']' in vartext[i]:
        scale[i]=scale[i-1]

varnames = [i.split(']')[0] if i.isupper() and ']' in i else None \
    for i in vartext]

# Make df
scaledf = pd.DataFrame({
    'Heading':heading,
    'Scale':scale,
    'Varname':varnames
})

# Some scales are not real scales
# They appear when Scale!=None and Varname==None
scaledf[233:236]

# Drop those
tempfilt = scaledf['Scale'].str.contains(']')!=True
scaledf = scaledf[tempfilt]

# Clean up dataframe:

# Some headings/scales have no varnames, but we want to keep them.
# We can solve this by first dropping any scales with None, 
# then dropping any varname that is None among those that have
# duplicated scales only

scaledf = scaledf[~scaledf['Scale'].isna()]
scaledf.reset_index(drop=True,inplace=True)
scaledf = scaledf[~scaledf['Varname'].isna() | \
                  ~scaledf['Scale'].duplicated(keep=False)]
scaledf.head()

# Import tree/root
tree=ET.ElementTree(file=urlopen("https://midus1-project1.ssc.wisc.edu/m1-p1-merged.ddi2.xml"))
root = tree.getroot()

# Topic Summary
topicsum = pd.DataFrame({'Source':pd.Series([i.attrib['name'] 
           for i in root.findall('dataDscr/varGrp') 
           if 'var' in i.attrib]).str.split('-',expand=True)[0],
        'Topic':[i.find('labl').text for i in root.findall('dataDscr/varGrp') 
        if 'var' in i.attrib]
        })

# Search for variables by string in label (description)  
def labsearch (search_string,root=root):
    search_string = search_string.lower()
    varnames = [i.attrib['name']
             for i in root.findall('dataDscr/var')
             if search_string in i.find('labl').text.lower() ]
    
    vardesc = [i.find('labl').text 
                  for i in root.findall('dataDscr/var')
                 if search_string in i.find('labl').text.lower() ]
    
    varqst = [None if i.find('qstn/qstnLit') is None
                 else i.find('qstn/qstnLit').text
                 for i in root.findall('dataDscr/var')
                if search_string in i.find('labl').text.lower() ]
    
    vartype = pd.Series(varnames).apply(lambda x: 
                                        [i.find('labl').text 
                                         for i in 
                                         root.findall('dataDscr/varGrp')
                                         if 'var' in i.attrib 
                                         and x in i.attrib['var']][0]
                                       )
    outdf = pd.DataFrame({
        'Variable':varnames,
        'Topic':vartype,
        'Description':vardesc,
        'Question':varqst
    })
    return outdf;

# Returns all variables by specified topic (must match exactly & case sensitive). For
# topic names see topicsum
def varbytopic (topic_string):
    varnames = pd.Series([i.attrib['var'] 
                         for i in root.findall('dataDscr/varGrp')
                         if 'var' in i.attrib 
                         and i.find('labl').text==topic_string])[0].split()
    varnames = pd.Series(varnames)
    vartype = varnames.apply(lambda x: [i.find('labl').text 
                                        for i in root.findall('dataDscr/varGrp')
                                        if 'var' in i.attrib
                                        and x in i.attrib['var']][0]
                                       )
    vardesc = varnames.apply(lambda x: [i.find('labl').text 
                                       for i in root.findall('dataDscr/var')
                                       if i.attrib['name'] == x ][0])
    varqst = varnames.apply(lambda x: [None if i.find('qstn/qstnLit') is None
                                      else i.find('qstn/qstnLit').text
                                      for i in root.findall('dataDscr/var')
                                      if i.attrib['name'] == x][0])
    
    outdf = pd.DataFrame({'Variable':varnames,
                          'Topic':vartype,
            'Description':vardesc,
            'Question':varqst})
    return outdf;

# Scale search: return computed scale varnames by search string
def scalesearch (search_string):
    search_string = search_string.lower()
    sfilter = scaledf['Heading'].str.lower().str.contains(search_string) | \
        scaledf['Scale'].str.lower().str.contains(search_string)
    return scaledf[sfilter]

# Variable of all MIDUS variable names
midusvars = pd.Series([i.attrib['name']
             for i in root.findall('dataDscr/var')])