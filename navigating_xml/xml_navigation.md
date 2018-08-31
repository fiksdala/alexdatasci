
__Table of Contents__

[Introduction](#intro)  
[Read in XML](#read_in_xml)  
[Explore the structure](#explore)  
[Extract information](#extract)  
[Make a function](#function)  
[Summary](#summary)  

<a id="intro"></a>
# Introduction

I'm working on coming up with an SVM classification project to post, and have been looking around for interesting, publicly available datasets to use. I've been considering looking at data from the Midlife in the United States Longitudinal Study (<a href="http://midus.wisc.edu/" target="_blank">MIDUS</a>)&ast;. This is a large dataset that is well-known in Social Psychology. It has the benefit of a large number of variables (>2000), but with that comes the challenge of sorting out what's actually included and what variables of interest you want to examine. This is always challenging with large datasets, since the variable names often take a form that are not super intuitive (e.g. X1, X2 ... X2000). The Inter-university Consortium for Political and Social Research hosts the data, and you could use their <a href="https://www.icpsr.umich.edu/icpsrweb/ICPSR/studies/2760/variables" target="_blank">website</a> to explore variables and search by keyword. When you download the data, there are also PDF files that summarize variables as well. These approaches are fine if you have a good idea of what you're looking for and the goal is not to automate any part of the analysis process, but it would be much easier and more convenient if you could incorporate this process in Python. This is where XML comes into play. Luckily, in addition to ICPSR website and PDF files, you can find an XML file that summarizes the data <a href="https://midus1-project1.ssc.wisc.edu/" target="_blank">here</a>. I'll use that file and Python's xml.etree.ElementTree module to write a function that will return variable names and details based on a search term.

&ast;MIDUS data is available to the public, but you must register first and agree to some very reasonable terms of use.  

__Resources__

I don't work with XML every day, so had to do a little searching to figure out how it works. If you're not familiar, I recommend you start by looking through the Python <a href="https://docs.python.org/3/library/xml.etree.elementtree.html#module-xml.etree.ElementTree" target="_blank">documentation</a> on ElementTree first. I also found Charles Severence's introduction <a href="https://www.youtube.com/watch?v=3OnGNUPxlho" target="_blank">video</a> helpful.

<a id="read_in_xml"></a>
# Read in XML

I'm not going to print out the XML file itself here, but I found it helpful to open it up in a text editor to get an idea of what's included and the structure of it. Once I did that, I figured out that I'm most interested in the dataDscr element, which also includes variable names, labels, and the text of the question itself (if applicable). Without actually printing the document, the basic structure of the stuff under dataDscr I'm really interested in looks something like this (though there's a ton more under "var" and other nodes that could be of interest):

`<var name="name">
    <labl>"label"</labl>
    <qstn>
        <qstnLit>"question text"</qstnLit>
    </qstn>
 </var>`

In order to access all that information, first I'll read in the XML file confirm things are in order by printing the elements of the root.


```python
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
tree = ET.parse('/Users/alex/Documents/alexdatasci/data_files/MIDUS_1/m1-p1-merged.ddi2.xml')
root = tree.getroot()
for i in root:
    print(i)
```

    <Element 'docDscr' at 0x1117769a8>
    <Element 'stdyDscr' at 0x11fdbfd18>
    <Element 'fileDscr' at 0x11fe37ae8>
    <Element 'dataDscr' at 0x11fe37bd8>


<a id="explore"></a>
# Explore the structure

The goal here is to be able to search through the text of the variable descriptions and questions for relevant words, and then return that information. This is where Python list comprehension comes in handy. For example, I can create a list of all of the variable descriptions:


```python
var_desc = [i.find('labl').text for i in root.findall('dataDscr/var')]
var_desc[0:4] # Show the first 5
```




    ['MIDUS 2 ID number',
     'MIDUS 2 Family number',
     'Major sample identification (aka Sample)',
     'Completion status of M1 respondents']



I can do the same for the questions that participants actually answered:


```python
var_questions = [i.text for i in root.findall('dataDscr/var/qstn/qstnLit')]
var_questions[0:5] # Show the first 5
```




    ['In general, would you say your PHYSICAL HEALTH is excellent, very good, good, fair, or poor?',
     'What about your MENTAL OR EMOTIONAL HEALTH? (Would you say your MENTAL OR EMOTIONAL HEALTH is excellent, very good, good, fair, or poor?)',
     'In general, compared to most men/women your age, would you say your health is much better, somewhat better, about the same, somewhat worse, or much worse?',
     'In the past 30 days, how many days were you TOTALLY UNABLE to go to work or carry out your normal household work activities because of your physical health or mental health?',
     'Was that due to your physical health, your mental health, or a combination of both?']



<a id="extract"></a>
# Extract information

Now that I can access the information, I'll have to come up with a way to extract what I want efficiently. One simple approach could be to just create a simple dataframe that consists of variable names, labels, and questions. This gets a little complicated though, since not all variables have questions, and my previous approach only returns values that exist. We can confirm that by looking at the lengths:


```python
print(len(var_desc))
print(len(var_questions))
```

    2095
    1405


We can solve that by using the "find" method with some more list comprehension. First I'll extract the questions, whether they exist or not, for all variables. Then I'll replace the missing values with an actual value.


```python
var_questions = ['None' if i.find('qstn/qstnLit')
                 is None else i.find('qstn/qstnLit').text 
                 for i in root.findall('dataDscr/var')]
print(var_questions[0:4]) # Print first 5
print([i for i in var_questions if i != 'None'][0:5]) # Print first 5 that are not none
```

    ['None', 'None', 'None', 'None']
    ['In general, would you say your PHYSICAL HEALTH is excellent, very good, good, fair, or poor?', 'What about your MENTAL OR EMOTIONAL HEALTH? (Would you say your MENTAL OR EMOTIONAL HEALTH is excellent, very good, good, fair, or poor?)', 'In general, compared to most men/women your age, would you say your health is much better, somewhat better, about the same, somewhat worse, or much worse?', 'In the past 30 days, how many days were you TOTALLY UNABLE to go to work or carry out your normal household work activities because of your physical health or mental health?', 'Was that due to your physical health, your mental health, or a combination of both?']


With this approach, you could pretty easily just make a dataframe of variable names, labels, and questions. You could then search that df for keywords. Alternatively, you could also skip that step and write a function that searches the XML file directly for what you want. That's what I'll do here. The goal is to write a function that takes a string, checks if that string is in in the variable label, then returns a dataframe containing the variable name, label, and associated question (if it has one).

<a id="function"></a>
# Make a function

First I'll test some of the basic concepts the function will requires. How can I use list comprehension to return a dataframe with all variable names, labels, and questions for variables that have the word 'heart' in the label?


```python
heartvars = [i.attrib['name']
             for i in root.findall('dataDscr/var')
             if 'heart' in i.find('labl').text.lower() ]

heartvars_desc = [i.find('labl').text 
                  for i in root.findall('dataDscr/var')
                 if 'heart' in i.find('labl').text.lower() ]

heartvars_qst = [None if i.find('qstn/qstnLit') is None
                 else i.find('qstn/qstnLit').text
                 for i in root.findall('dataDscr/var')
                if 'heart' in i.find('labl').text.lower() ]
# Have to specify None since .text won't work if it's empty.

pd.DataFrame({
    'Variable':heartvars,
    'Description':heartvars_desc,
    'Question':heartvars_qst
}).head()
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Variable</th>
      <th>Description</th>
      <th>Question</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>A1PA11</td>
      <td>Heart problems ever</td>
      <td>Have you ever had heart trouble suspected or c...</td>
    </tr>
    <tr>
      <th>1</th>
      <td>A1PA11A</td>
      <td>Age of heart problem</td>
      <td>How old were you when a doctor first told you ...</td>
    </tr>
    <tr>
      <th>2</th>
      <td>A1PA11BA</td>
      <td>Heart attack</td>
      <td>What was the diagnosis - HEART ATTACK?</td>
    </tr>
    <tr>
      <th>3</th>
      <td>A1PA11BE</td>
      <td>Hole in heart/atrial septal dfct</td>
      <td>What was the diagnosis - HOLE IN HEART, ATRIAL...</td>
    </tr>
    <tr>
      <th>4</th>
      <td>A1PA11BG</td>
      <td>Irregular/fast heart beat/arrhyt</td>
      <td>What was the diagnosis - IRREGULAR/FAST HEART ...</td>
    </tr>
  </tbody>
</table>
</div>



Alright, that's pretty cool! Applying that concept to a function is pretty straightforward:


```python
def varsearch (search_string,root=root):
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
    outdf = pd.DataFrame({
        'Variable':varnames,
        'Description':vardesc,
        'Question':varqst
    })
    return outdf;

varsearch('heart').head()
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Variable</th>
      <th>Description</th>
      <th>Question</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>A1PA11</td>
      <td>Heart problems ever</td>
      <td>Have you ever had heart trouble suspected or c...</td>
    </tr>
    <tr>
      <th>1</th>
      <td>A1PA11A</td>
      <td>Age of heart problem</td>
      <td>How old were you when a doctor first told you ...</td>
    </tr>
    <tr>
      <th>2</th>
      <td>A1PA11BA</td>
      <td>Heart attack</td>
      <td>What was the diagnosis - HEART ATTACK?</td>
    </tr>
    <tr>
      <th>3</th>
      <td>A1PA11BE</td>
      <td>Hole in heart/atrial septal dfct</td>
      <td>What was the diagnosis - HOLE IN HEART, ATRIAL...</td>
    </tr>
    <tr>
      <th>4</th>
      <td>A1PA11BG</td>
      <td>Irregular/fast heart beat/arrhyt</td>
      <td>What was the diagnosis - IRREGULAR/FAST HEART ...</td>
    </tr>
  </tbody>
</table>
</div>



That is super convenient, and way easier than navigating a website or reading through a huge PDF file. What's better, now that it's in a Pandas dataframe, you can extract the variable names directly and use that to subset the larger data file later on.

<a id="summary"></a>
# Summary

So there you have it. If a dataset with a lot of variables has an associated XML file, using ElementTree to parse thorugh everything can help a lot as you start looking at what questions you can answer and problems you can solve with the data. Wrap everything in a function, and you can quickly get a sense of what kind of variables are available. I also like the idea of sticking with parsing XML directly with a function like this because you can easily add more attributes to the function if you need more information. For example, this file also contains value labels and some other information like minimum and maximum values that, if needed, can easily be added to the function. 

Next week I'm planning on on posting a little SVM project, also using Python, maybe using this dataset (I haven't decided yet). As always, if you have questions or would like to get in touch, you can contact me at alex@alexdatasci.com. 

Happy Weekend!

-Alex
