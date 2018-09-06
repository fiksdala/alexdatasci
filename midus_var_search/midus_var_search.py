from urllib.request import urlopen
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET

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
def varsearch (search_string,root=root):
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
