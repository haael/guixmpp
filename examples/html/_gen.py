#!/usr/bin/python3

from bs4 import BeautifulSoup
import glob
import os
from html import escape


# Define the basic structure of an HTML file with a placeholder for the content
def create_html_file(tag_name, examples, description):
    soup = BeautifulSoup(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Example of {tag_name}</title>
    </head>
    <body>
    </body>
    </html>
    """, 'html.parser')

    # Add content to the body
    body = soup.body
    body.append(soup.new_tag('h1'))
    body.h1.string = f"Example of <{tag_name}>"

    # Add description
    body.append(soup.new_tag('p'))
    body.p.string = description

    # Insert the example content
    for example in examples:
        body.append(BeautifulSoup(example, 'html.parser'))

    return str(soup)


# List of tags to create examples for
tags = [
    ('a', '<a href="https://example.com">This is {NUMBER} link to Example.com</a>', 'The <a> tag defines a hyperlink.'),
    ('abbr', '<abbr title="HyperText Markup Language{NUMBER}">HTML{NUMBER}</abbr>', 'The <abbr> tag defines an abbreviated form of a longer word or phrase.'),
    ('address', '<address>Contact {NUMBER}: <a href="mailto:info{NUMBER}@example.com">info{NUMBER}@example.com</a></address>', 'The <address> tag specifies the author\'s contact information.'),
    ('area', '<map name="workmap{NUMBER}"><area shape="rect" coords="34,44,270,350" alt="Computer{NUMBER}" href="computer{NUMBER}.htm"></map>', 'The <area> tag defines a specific area within an image map.'),
    ('article', '<article><h2>Article Title {NUMBER}</h2><p>Article content {NUMBER}.</p></article>', 'The <article> tag defines an article.'),
    ('aside', '<aside><h3>Aside Title {NUMBER}</h3><p>Aside content {NUMBER}.</p></aside>', 'The <aside> tag defines some content loosely related to the page content.'),
    ('audio', '<audio controls><source src="audio{NUMBER}.mp3" type="audio/mpeg">Your browser does not support the audio element {NUMBER}.</audio>', 'The <audio> tag embeds a sound or an audio stream in an HTML document.'),
    ('b', '<p>This is <b>bold text {NUMBER}</b>.</p>', 'The <b> tag displays text in a bold style.'),
    ('base', '<base href="https://example{NUMBER}.com/" target="_blank">', 'The <base> tag defines the base URL for all relative URLs in a document.'),
    ('bdi', '<p>This text will go left <bdi>this text will go right {NUMBER}</bdi>.</p>', 'The <bdi> tag represents text that is isolated from its surrounding for the purposes of bidirectional text formatting.'),
    ('bdo', '<bdo dir="rtl">This text will go right to left {NUMBER}.</bdo>', 'The <bdo> tag overrides the current text direction.'),
    ('blockquote', '<blockquote cite="https://example{NUMBER}.com">This is a long quotation {NUMBER}.</blockquote>', 'The <blockquote> tag represents a section that is quoted from another source.'),
    ('br', '<p>Line break {NUMBER}<br>example {NUMBER}.</p>', 'The <br> tag produces a single line break.'),
    ('button', '<button type="button">Click Me! {NUMBER}</button>', 'The <button> tag creates a clickable button.'),
    ('canvas', '<canvas id="myCanvas{NUMBER}" width="200" height="100" style="border:1px solid #000000;"></canvas>', 'The <canvas> tag defines a region in the document for drawing graphics on the fly via scripting.'),
    ('caption', '<table><caption>Table Caption {NUMBER}</caption><tr><td>Table Data {NUMBER}</td></tr></table>', 'The <caption> tag defines the caption or title of the table.'),
    ('cite', '<p><cite>This is a citation {NUMBER}</cite>.</p>', 'The <cite> tag indicates a citation or reference to another source.'),
    ('code', '<p>This is <code>computer code {NUMBER}</code>.</p>', 'The <code> tag specifies text as computer code.'),
    ('col', '<table><colgroup><col span="2" style="background-color:red"></colgroup><tr><td>Cell {NUMBER}</td><td>Cell {NUMBER+1}</td></tr></table>', 'The <col> tag defines attribute values for one or more columns in a table.'),
    ('colgroup', '<table><colgroup><col span="2" style="background-color:red"><col style="background-color:yellow"></colgroup><tr><td>Cell {NUMBER}</td><td>Cell {NUMBER+1}</td><td>Cell {NUMBER+2}</td></tr></table>', 'The <colgroup> tag specifies attributes for multiple columns in a table.'),
    ('data', '<p>Product code {NUMBER}: <data value="98765{NUMBER}">987-65{NUMBER}</data></p>', 'The <data> tag links a piece of content with a machine-readable translation.'),
    ('datalist', '<input list="browsers{NUMBER}"><datalist id="browsers{NUMBER}"><option value="Chrome{NUMBER}"><option value="Firefox{NUMBER}"><option value="Safari{NUMBER}"></datalist>', 'The <datalist> tag represents a set of pre-defined options for an <input> element.'),
    ('dd', '<dl><dt>Term {NUMBER}</dt><dd>Description of the term {NUMBER}</dd></dl>', 'The <dd> tag specifies a description or value for the term (<dt>) in a description list (<dl>).'),
    ('del', '<p>This is <del>deleted {NUMBER}</del> text.</p>', 'The <del> tag represents text that has been deleted from the document.'),
    ('details', '<details><summary>More Info {NUMBER}</summary><p>Details here {NUMBER}.</p></details>', 'The <details> tag represents a widget from which the user can obtain additional information or controls on-demand.'),
    ('dfn', '<p><dfn>HTML {NUMBER}</dfn> is the standard markup language for creating web pages.</p>', 'The <dfn> tag specifies a definition.'),
    ('dialog', '<dialog open>This is an open dialog window {NUMBER}.</dialog>', 'The <dialog> tag defines a dialog box or subwindow.'),
    ('div', '<div>This is a division or section in a document {NUMBER}.</div>', 'The <div> tag specifies a division or a section in a document.'),
    ('dl', '<dl><dt>Term {NUMBER}</dt><dd>Description {NUMBER}</dd><dt>Term {NUMBER+1}</dt><dd>Description {NUMBER+1}</dd></dl>', 'The <dl> tag defines a description list.'),
    ('dt', '<dl><dt>Term {NUMBER}</dt><dd>Description of the term {NUMBER}</dd></dl>', 'The <dt> tag defines a term (an item) in a description list.'),
    ('em', '<p>This is <em>emphasized {NUMBER}</em> text.</p>', 'The <em> tag defines emphasized text.'),
    ('embed', '<embed src="example{NUMBER}.swf">', 'The <embed> tag embeds external applications, typically multimedia content like audio or video, into an HTML document.'),
    ('fieldset', '<form><fieldset><legend>Personal Information {NUMBER}:</legend><label for="fname{NUMBER}">First name:</label><input type="text" id="fname{NUMBER}" name="fname"></fieldset></form>', 'The <fieldset> tag specifies a set of related form fields.'),
    ('figcaption', '<figure><img src="example{NUMBER}.jpg" alt="Example"><figcaption>Caption for the image {NUMBER}</figcaption></figure>', 'The <figcaption> tag defines a caption or legend for a figure.'),
    ('figure', '<figure><img src="example{NUMBER}.jpg" alt="Example"><figcaption>Caption for the image {NUMBER}</figcaption></figure>', 'The <figure> tag represents a figure illustrated as part of the document.'),
    ('footer', '<footer><p>Author {NUMBER}: Someone</p></footer>', 'The <footer> tag represents the footer of a document or a section.'),
    ('form', '<form action="/submit{NUMBER}" method="post"><label for="name{NUMBER}">Name:</label><input type="text" id="name{NUMBER}" name="name"><input type="submit" value="Submit"></form>', 'The <form> tag defines an HTML form for user input.'),
    ('h1', '<h1>This is a Heading 1 {NUMBER}</h1>', 'The <h1> tag defines a top-level heading.'),
    ('h2', '<h2>This is a Heading 2 {NUMBER}</h2>', 'The <h2> tag defines a second-level heading.'),
    ('h3', '<h3>This is a Heading 3 {NUMBER}</h3>', 'The <h3> tag defines a third-level heading.'),
    ('h4', '<h4>This is a Heading 4 {NUMBER}</h4>', 'The <h4> tag defines a fourth-level heading.'),
    ('h5', '<h5>This is a Heading 5 {NUMBER}</h5>', 'The <h5> tag defines a fifth-level heading.'),
    ('h6', '<h6>This is a Heading 6 {NUMBER}</h6>', 'The <h6> tag defines a sixth-level heading.'),
    ('header', '<header><h1>Website Header {NUMBER}</h1></header>', 'The <header> tag represents the header of a document or a section.'),
    ('hr', '<p>This is a paragraph {NUMBER}.</p><hr><p>This is another paragraph {NUMBER}.</p>', 'The <hr> tag produces a horizontal line.'),
    ('i', '<p>This is <i>italic {NUMBER}</i> text.</p>', 'The <i> tag displays text in an italic style.'),
    ('iframe', '<iframe src="https://example{NUMBER}.com" width="600" height="400"></iframe>', 'The <iframe> tag displays a URL in an inline frame.'),
    ('img', '<img src="example{NUMBER}.jpg" alt="Example Image {NUMBER}">', 'The <img> tag represents an image.'),
    ('input', '<form><label for="username{NUMBER}">Username:</label><input type="text" id="username{NUMBER}" name="username"></form>', 'The <input> tag defines an input control.'),
    ('ins', '<p>This is <ins>inserted {NUMBER}</ins> text.</p>', 'The <ins> tag defines a block of text that has been inserted into a document.'),
    ('kbd', '<p>Press <kbd>Ctrl</kbd> + <kbd>C {NUMBER}</kbd> to copy.</p>', 'The <kbd> tag specifies text as keyboard input.'),
    ('label', '<form><label for="username{NUMBER}">Username:</label><input type="text" id="username{NUMBER}" name="username"></form>', 'The <label> tag defines a label for an <input> control.'),
    ('legend', '<form><fieldset><legend>Personal Information {NUMBER}:</legend><label for="fname{NUMBER}">First name:</label><input type="text" id="fname{NUMBER}" name="fname"></fieldset></form>', 'The <legend> tag defines a caption for a <fieldset> element.'),
    ('li', '<ul><li>List Item {NUMBER}</li><li>List Item {NUMBER+1}</li></ul>', 'The <li> tag defines a list item.'),
    ('main', '<main><h1>Main Content {NUMBER}</h1><p>This is the main content of the document {NUMBER}.</p></main>', 'The <main> tag represents the main or dominant content of the document.'),
    ('map', '<img src="workplace{NUMBER}.jpg" alt="Workplace" usemap="#workmap{NUMBER}"><map name="workmap{NUMBER}"><area shape="rect" coords="34,44,270,350" alt="Computer" href="computer{NUMBER}.htm"></map>', 'The <map> tag defines a client-side image-map.'),
    ('mark', '<p>This is <mark>highlighted {NUMBER}</mark> text.</p>', 'The <mark> tag represents text highlighted for reference purposes.'),
    ('menu', '<menu><li><button onclick="copyText{NUMBER}()">Copy</button></li><li><button onclick="cutText{NUMBER}()">Cut</button></li></menu>', 'The <menu> tag represents a list of commands.'),
    ('meter', '<meter value="0.{NUMBER}">0.{NUMBER}%</meter>', 'The <meter> tag represents a scalar measurement within a known range.'),
    ('nav', '<nav><a href="/home{NUMBER}">Home</a> | <a href="/about{NUMBER}">About</a> | <a href="/contact{NUMBER}">Contact</a></nav>', 'The <nav> tag defines a section of navigation links.'),
    ('noscript', '<noscript>Your browser does not support JavaScript! {NUMBER}</noscript>', 'The <noscript> tag defines alternative content to display when the browser doesn\'t support scripting.'),
    ('object', '<object data="example{NUMBER}.pdf" width="300" height="200"></object>', 'The <object> tag defines an embedded object.'),
    ('ol', '<ol><li>Ordered List Item {NUMBER}</li><li>Ordered List Item {NUMBER+1}</li></ol>', 'The <ol> tag defines an ordered list.'),
    ('optgroup', '<select><optgroup label="Group {NUMBER}"><option value="option{NUMBER}">Option {NUMBER}</option></optgroup></select>', 'The <optgroup> tag defines a group of related options in a selection list.'),
    ('option', '<select><option value="option{NUMBER}">Option {NUMBER}</option></select>', 'The <option> tag defines an option in a selection list.'),
    ('output', '<form oninput="result{NUMBER}.value=parseInt(a{NUMBER}.value)+parseInt(b{NUMBER}.value)"><input type="range" id="a{NUMBER}" value="50"> + <input type="number" id="b{NUMBER}" value="25"> = <output name="result{NUMBER}" for="a{NUMBER} b{NUMBER}">75</output></form>', 'The <output> tag represents the result of a calculation.'),
    ('p', '<p>This is a paragraph {NUMBER}.</p>', 'The <p> tag defines a paragraph.'),
    ('picture', '<picture><source media="(min-width:650px)" srcset="img_pink_flowers{NUMBER}.jpg"><source media="(min-width:465px)" srcset="img_white_flower{NUMBER}.jpg"><img src="img_orange_flowers{NUMBER}.jpg" alt="Flowers"></picture>', 'The <picture> tag defines a container for multiple image sources.'),
    ('pre', '<pre>This text is preformatted {NUMBER}.</pre>', 'The <pre> tag defines a block of preformatted text.'),
    ('progress', '<progress value="{NUMBER}" max="100">{NUMBER}%</progress>', 'The <progress> tag represents the completion progress of a task.'),
    ('q', '<p>This is a <q>short quotation {NUMBER}</q>.</p>', 'The <q> tag defines a short inline quotation.'),
    ('rp', '<ruby>漢 <rp>(</rp><rt>kan</rt><rp>)</rp>字 <rp>(</rp><rt>ji</rt><rp>)</rp></ruby> {NUMBER}', 'The <rp> tag provides fall-back parentheses for browsers that don\'t support ruby annotations.'),
    ('rt', '<ruby>漢 <rt>kan</rt>字 <rt>ji</rt></ruby> {NUMBER}', 'The <rt> tag defines the pronunciation of characters presented in a ruby annotation.'),
    ('ruby', '<ruby>漢 <rt>kan</rt>字 <rt>ji</rt></ruby> {NUMBER}', 'The <ruby> tag represents a ruby annotation.'),
    ('s', '<p>This is <s>strikethrough {NUMBER}</s> text.</p>', 'The <s> tag represents contents that are no longer accurate or no longer relevant.'),
    ('samp', '<p>This is <samp>sample output {NUMBER}</samp> from a computer program.</p>', 'The <samp> tag specifies text as sample output from a computer program.'),
    ('section', '<section><h2>Section Title {NUMBER}</h2><p>Section content {NUMBER}.</p></section>', 'The <section> tag defines a section of a document.'),
    ('select', '<form><label for="cars{NUMBER}">Choose a car:</label><select id="cars{NUMBER}" name="cars"><option value="volvo">Volvo</option><option value="saab">Saab</option></select></form>', 'The <select> tag defines a selection list within a form.'),
    ('small', '<p>This is <small>smaller {NUMBER}</small> text.</p>', 'The <small> tag displays text in a smaller size.'),
    ('source', '<audio controls><source src="audio{NUMBER}.mp3" type="audio/mpeg"></audio>', 'The <source> tag defines alternative media resources for media elements like <audio> or <video>.'),
    ('span', '<p>This is a <span style="color:red">span {NUMBER}</span> of text.</p>', 'The <span> tag defines an inline styleless section in a document.'),
    ('strong', '<p>This is <strong>strongly emphasized {NUMBER}</strong> text.</p>', 'The <strong> tag indicates strongly emphasized text.'),
    ('sub', '<p>This is <sub>subscripted {NUMBER}</sub> text.</p>', 'The <sub> tag defines subscripted text.'),
    ('summary', '<details><summary>More Info {NUMBER}</summary><p>Details here {NUMBER}.</p></details>', 'The <summary> tag defines a summary for the <details> element.'),
    ('sup', '<p>This is <sup>superscripted {NUMBER}</sup> text.</p>', 'The <sup> tag defines superscripted text.'),
    ('table', '<table><tr><td>Table Data {NUMBER}</td></tr></table>', 'The <table> tag defines a data table.'),
    ('tbody', '<table><tbody><tr><td>Body Data {NUMBER}</td></tr></tbody></table>', 'The <tbody> tag groups a set of rows defining the main body of the table data.'),
    ('td', '<table><tr><td>Table Data {NUMBER}</td></tr></table>', 'The <td> tag defines a cell in a table.'),
    ('textarea', '<form><textarea name="message{NUMBER}" rows="10" cols="30">The cat was playing in the garden {NUMBER}.</textarea></form>', 'The <textarea> tag defines a multi-line text input control.'),
    ('tfoot', '<table><tfoot><tr><td>Footer Data {NUMBER}</td></tr></tfoot></table>', 'The <tfoot> tag groups a set of rows summarizing the columns of the table.'),
    ('th', '<table><tr><th>Header Data {NUMBER}</th></tr></table>', 'The <th> tag defines a header cell in a table.'),
    ('thead', '<table><thead><tr><th>Header Data {NUMBER}</th></tr></thead></table>', 'The <thead> tag groups a set of rows that describes the column labels of a table.'),
    ('time', '<p>The event starts at <time datetime="2023-12-31T20:00">8:00 PM {NUMBER}</time>.</p>', 'The <time> tag represents a time and/or date.'),
    ('tr', '<table><tr><td>Row Data {NUMBER}</td></tr></table>', 'The <tr> tag defines a row of cells in a table.'),
    ('track', '<video controls><source src="video{NUMBER}.mp4" type="video/mp4"><track src="subtitles_en{NUMBER}.vtt" kind="subtitles" srclang="en" label="English"></video>', 'The <track> tag defines text tracks for media elements like <audio> or <video>.'),
    ('u', '<p>This is <u>underlined {NUMBER}</u> text.</p>', 'The <u> tag displays text with an underline.'),
    ('ul', '<ul><li>Unordered List Item {NUMBER}</li><li>Unordered List Item {NUMBER+1}</li></ul>', 'The <ul> tag defines an unordered list.'),
    ('var', '<p>This is a <var>variable {NUMBER}</var>.</p>', 'The <var> tag defines a variable.'),
    ('video', '<video controls><source src="video{NUMBER}.mp4" type="video/mp4">Your browser does not support the video tag {NUMBER}.</video>', 'The <video> tag embeds video content in an HTML document.'),
    ('wbr', '<p>This is a longwordthatmightneedto<wbr>break {NUMBER}.</p>', 'The <wbr> tag represents a line break opportunity.')
]


# List of display attribute values to create examples for
display_attributes = [
    ('inline', '<div style="display: inline; border: 1px solid black;">This is an inline div {NUMBER}.</div>', 'Displays an element as an inline element (like <span>).'),
    ('block', '<div style="display: block; border: 1px solid black;">This is a block div {NUMBER}.</div>', 'Displays an element as a block element (like <p>).'),
    ('contents', '<div style="display: contents; border: 1px solid black;">This is a contents div {NUMBER}.</div>', 'Makes the container disappear, making the child elements children of the element the next level up in the DOM.'),
    ('flex', '<div style="display: flex; border: 1px solid black;">This is a flex div {NUMBER}.</div>', 'Displays an element as a block-level flex container.'),
    ('grid', '<div style="display: grid; border: 1px solid black;">This is a grid div {NUMBER}.</div>', 'Displays an element as a block-level grid container.'),
    ('inline-block', '<div style="display: inline-block; border: 1px solid black;">This is an inline-block div {NUMBER}.</div>', 'Displays an element as an inline-level block container.'),
    ('inline-flex', '<div style="display: inline-flex; border: 1px solid black;">This is an inline-flex div {NUMBER}.</div>', 'Displays an element as an inline-level flex container.'),
    ('inline-grid', '<div style="display: inline-grid; border: 1px solid black;">This is an inline-grid div {NUMBER}.</div>', 'Displays an element as an inline-level grid container.'),
    ('inline-table', '<div style="display: inline-table; border: 1px solid black;">This is an inline-table div {NUMBER}.</div>', 'The element is displayed as an inline-level table.'),
    ('list-item', '<div style="display: list-item; border: 1px solid black;">This is a list-item div {NUMBER}.</div>', 'Let the element behave like a <li> element.'),
    ('run-in', '<div style="display: run-in; border: 1px solid black;">This is a run-in div {NUMBER}.</div>', 'Displays an element as either block or inline, depending on context.'),
    ('table', '<div style="display: table; border: 1px solid black;">This is a table div {NUMBER}.</div>', 'Let the element behave like a <table> element.'),
    ('table-caption', '<div style="display: table-caption; border: 1px solid black;">This is a table-caption div {NUMBER}.</div>', 'Let the element behave like a <caption> element.'),
    ('table-column-group', '<div style="display: table-column-group; border: 1px solid black;">This is a table-column-group div {NUMBER}.</div>', 'Let the element behave like a <colgroup> element.'),
    ('table-header-group', '<div style="display: table-header-group; border: 1px solid black;">This is a table-header-group div {NUMBER}.</div>', 'Let the element behave like a <thead> element.'),
    ('table-footer-group', '<div style="display: table-footer-group; border: 1px solid black;">This is a table-footer-group div {NUMBER}.</div>', 'Let the element behave like a <tfoot> element.'),
    ('table-row-group', '<div style="display: table-row-group; border: 1px solid black;">This is a table-row-group div {NUMBER}.</div>', 'Let the element behave like a <tbody> element.'),
    ('table-cell', '<div style="display: table-cell; border: 1px solid black;">This is a table-cell div {NUMBER}.</div>', 'Let the element behave like a <td> element.'),
    ('table-column', '<div style="display: table-column; border: 1px solid black;">This is a table-column div {NUMBER}.</div>', 'Let the element behave like a <col> element.'),
    ('table-row', '<div style="display: table-row; border: 1px solid black;">This is a table-row div {NUMBER}.</div>', 'Let the element behave like a <tr> element.'),
    ('none', '<div style="display: none; border: 1px solid black;">This is a none div {NUMBER}.</div>', 'The element is completely removed.')
]


# Generate a file with five divs containing ten spans each, with different display attributes
div_spans_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Div and Span Display Examples</title>
    <style>
        div {{ display: {}; }}
    </style>
</head>
<body>
    <h1>Div and Span Display Examples</h1>
    <h2>display: {};</h2>
    <h3>{}</h3>
    <div>
        <span>Span 1</span><span>Span 2</span><span>Span 3</span><span>Span 4</span><span>Span 5</span>
        <span>Span 6</span><span>Span 7</span><span>Span 8</span><span>Span 9</span><span>Span 10</span>
    </div>
    <div>
        <span>Span 1</span><span>Span 2</span><span>Span 3</span><span>Span 4</span><span>Span 5</span>
        <span>Span 6</span><span>Span 7</span><span>Span 8</span><span>Span 9</span><span>Span 10</span>
    </div>
    <div>
        <span>Span 1</span><span>Span 2</span><span>Span 3</span><span>Span 4</span><span>Span 5</span>
        <span>Span 6</span><span>Span 7</span><span>Span 8</span><span>Span 9</span><span>Span 10</span>
    </div>
    <div>
        <span>Span 1</span><span>Span 2</span><span>Span 3</span><span>Span 4</span><span>Span 5</span>
        <span>Span 6</span><span>Span 7</span><span>Span 8</span><span>Span 9</span><span>Span 10</span>
    </div>
    <div>
        <span>Span 1</span><span>Span 2</span><span>Span 3</span><span>Span 4</span><span>Span 5</span>
        <span>Span 6</span><span>Span 7</span><span>Span 8</span><span>Span 9</span><span>Span 10</span>
    </div>
</body>
</html>
"""


table_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Div and Span Display Examples</title>
</head>
<body>
    <h1>Table Examples</h1>

  <table>
    <tr>
        <td>Cell 0,0 aaaa aaaa aaaa aaaa bbbb bbbb bbbb bbbb cccc cccc cccc cccc dddd dddd dddd dddd</td> <td>Cell 0,1</td> <td>Cell 0,2 aaaa aaaa aaaa aaaa bbbb bbbb bbbb bbbb cccc cccc cccc cccc dddd dddd dddd dddd</td> <td>Cell 0,3</td> <td>Cell 0,4</td>
        <td>Cell 0,5</td> <td>Cell 0,6</td> <td>Cell 0,7</td> <td>Cell 0,8</td> <td>Cell 0,9</td>
    </tr>
    <tr>
        <td>Cell 0,0</td> <td>Cell 0,1</td> <td>Cell 0,2 aaaa aaaa aaaa aaaa bbbb bbbb bbbb bbbb cccc cccc cccc cccc dddd dddd dddd dddd</td> <td>Cell 0,3</td> <td>Cell 0,4 aaaa aaaa aaaa aaaa bbbb bbbb bbbb bbbb cccc cccc cccc cccc dddd dddd dddd dddd</td>
        <td>Cell 0,5</td> <td>Cell 0,6</td> <td>Cell 0,7</td> <td>Cell 0,8</td> <td>Cell 0,9 aaaa aaaa aaaa aaaa<br/> bbbb bbbb bbbb bbbb cccc cccc cccc cccc dddd dddd dddd dddd</td>
    </tr>
    <tr>
        <td>Cell 0,0</td> <td>Cell 0,1</td> <td>Cell 0,2</td> <td>Cell 0,3</td> <td>Cell 0,4</td>
        <td>Cell 0,5 aaaa aaaa aaaa aaaa bbbb bbbb bbbb bbbb<br/> cccc cccc cccc cccc<br/> dddd dddd dddd dddd</td> <td>Cell 0,6</td> <td>Cell 0,7 aaaa aaaa aaaa aaaa bbbb bbbb bbbb bbbb cccc cccc cccc cccc dddd dddd dddd dddd</td> <td>Cell 0,8</td> <td>Cell 0,9</td>
    </tr>
    <tr>
        <td>Cell 0,0</td> <td>Cell 0,1</td> <td>Cell 0,2</td> <td>Cell 0,3</td> <td>Cell 0,4</td>
        <td>Cell 0,5</td> <td>Cell 0,6</td> <td>Cell 0,7</td> <td>Cell 0,8</td> <td>Cell 0,9</td>
    </tr>
    <tr>
        <td>Cell 0,0</td> <td>Cell 0,1</td> <td>Cell 0,2</td> <td>Cell 0,3</td> <td>Cell 0,4 aaaa aaaa aaaa aaaa<br/> bbbb bbbb bbbb bbbb cccc cccc cccc cccc dddd dddd dddd dddd</td>
        <td>Cell 0,5</td> <td>Cell 0,6</td> <td>Cell 0,7</td> <td>Cell 0,8</td> <td>Cell 0,9</td>
    </tr>
  </table>

</body>
</html>
"""


# Generate the index.html file with links to all examples
index_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HTML Tag Examples</title>
</head>
<body>
    <h1>HTML Tag Examples</h1>
    <ul>
        {"".join([f"<li><a href='{tag_name}.html'>{tag_name}</a>: {escape(description)}</li>" for tag_name, _, description in tags])}
    </ul>
    <h1>CSS Display Attribute Examples</h1>
    <ul>
        {"".join([f"<li><a href='display_{attr_name}.html'>{attr_name}</a>: {escape(description)}</li>" for attr_name, _, description in display_attributes])}
    </ul>
    <h1>CSS Display Attribute Examples 2</h1>
    <ul>
        {"".join([f"<li><a href='divspans_{attr_name}.html'>{attr_name}</a>: {escape(description)}</li>" for attr_name, _, description in display_attributes])}
    </ul>
    <h1>Table examples</h1>
    <ul>
        <li><a href='table_1.html'>table 1</a>: Table 1</li>
    </ul>
</body>
</html>
"""


if __name__ == '__main__':
	# Remove all existing HTML files in the current directory
	for file in glob.glob("*.html"):
		os.remove(file)

	# Generate HTML files for each tag
	for tag_name, template, description in tags:
		examples = [template.replace('{NUMBER}', str(i)).replace('{NUMBER+1}', str(i+1)).replace('{NUMBER+2}', str(i+2)) for i in range(1, 11)]
		html_content = create_html_file(tag_name, examples, description)
		file_path = f'{tag_name}.html'
		with open(file_path, 'w') as file:
		    file.write(html_content)

	# Generate HTML files for each display attribute
	for attr_name, template, description in display_attributes:
		examples = [template.replace('{NUMBER}', str(i)) for i in range(1, 11)]
		html_content = create_html_file(attr_name, examples, description)
		file_path = f'display_{attr_name}.html'
		with open(file_path, 'w') as file:
		    file.write(html_content)

	# Generate HTML files for each display attribute
	for attr_name, template, description in display_attributes:
		file_path = f'divspans_{attr_name}.html'
		with open(file_path, 'w') as file:
		    file.write(div_spans_content.format(attr_name, attr_name, escape(description)))

	with open('table_1.html', 'w') as table_file:
		table_file.write(table_content)

	with open('_index.html', 'w') as index_file:
		index_file.write(index_content)




