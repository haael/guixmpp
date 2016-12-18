<?xml version="1.0" ?>

<stylesheet version="1.0"
 xmlns="http://www.w3.org/1999/XSL/Transform"
 xmlns:a="http://haael.net/2014/app"
 xmlns:f="http://www.w3.org/2002/xforms"
 undeclare-prefixes="yes"
 exclude-result-prefixes="a f"
 >

 <output method="xml" indent="yes"/>
 <strip-space elements="*"/>

 <template match="/a:app">

  <element name="html" namespace="http://www.w3.org/1999/xhtml">
   <element name="head"  namespace="http://www.w3.org/1999/xhtml">
    <apply-templates select="f:model"/>

    <element name="style"  namespace="http://www.w3.org/1999/xhtml">
     <attribute name="type">text/css</attribute>
     <text>

body { font-family: sans-serif; }

.spacer { background: #eeeeff; }
.xforms-control { background:orange; }

body > div.hbox, body > div.vbox { width:100vw; height:100vh; }
.hbox { display:flex; flex-direction:row; vertical-align:middle; }
.vbox { display:flex; flex-direction:column; vertical-align:middle; }
.xforms-control { display:inline-flex; }

.hbox, .vbox { flex:0 1 auto; }
.spacer { flex:1 1 0; }

.hbox > .xforms-control { width:100%; }
.vbox > .xforms-control { flex:1 1 auto; }
.xforms-control > * { flex:0 1 auto; }
.xforms-control > .value { flex:1 1 0; }
input.xforms-value { width:calc(100% - 4px); border:1px solid black; font:inherit; }
.xforms-textarea { flex:1 1 0; }
textarea.xforms-value { resize:none; width:calc(100% - 4px); border:1px solid black; font:inherit; }
button { width:100%; height:100%; border:1px outline black; background:inherit; font:inherit; }

label { white-space:pre; }

     </text>
    </element>

   </element>
   <element name="body" namespace="http://www.w3.org/1999/xhtml">
    <apply-templates select="a:vbox|a:hbox"/>
   </element>
  </element>
 </template>

 <template match="f:*">
  <copy-of select="."/>
 </template>

 <template match="a:hbox">
  <element name="div" namespace="http://www.w3.org/1999/xhtml">
   <attribute name="class">hbox</attribute>
   <attribute name="style">
    <text>flex:</text>
    <choose>
     <when test="@expand"><value-of select="@expand"/></when>
     <otherwise><text>0</text></otherwise>
    </choose>
    <text> 0 </text>
    <choose>
     <when test="@size"><value-of select="@size"/></when>
     <otherwise><text>auto</text></otherwise>
    </choose>
    <text>;</text>
   </attribute>
   <apply-templates/>
  </element>
 </template>

 <template match="a:vbox">
  <element name="div" namespace="http://www.w3.org/1999/xhtml">
   <attribute name="class">vbox</attribute>
   <attribute name="style">
    <text>flex:</text>
    <choose>
     <when test="@expand"><value-of select="@expand"/></when>
     <otherwise><text>0</text></otherwise>
    </choose>
    <text> 0 </text>
    <choose>
     <when test="@size"><value-of select="@size"/></when>
     <otherwise><text>auto</text></otherwise>
    </choose>
    <text>;</text>
   </attribute>
   <apply-templates/>
  </element>
 </template>

 <template match="a:hbox/a:space">
  <element name="span" namespace="http://www.w3.org/1999/xhtml">
   <attribute name="class">spacer</attribute>
   <attribute name="style">
    <text>flex:</text>
    <choose>
     <when test="@expand"><value-of select="@expand"/></when>
     <otherwise><text>1</text></otherwise>
    </choose>
    <text> 0 </text>
    <choose>
     <when test="@size"><value-of select="@size"/></when>
     <otherwise><text>0</text></otherwise>
    </choose>
    <text>;</text>
   </attribute>
   <text> </text>
  </element>
 </template>

 <template match="a:vbox/a:space">
  <element name="div" namespace="http://www.w3.org/1999/xhtml">
   <attribute name="class">spacer</attribute>
   <attribute name="style">
    <text>flex:</text>
    <choose>
     <when test="@expand"><value-of select="@expand"/></when>
     <otherwise><text>1</text></otherwise>
    </choose>
    <text> 0 </text>
    <choose>
     <when test="@size"><value-of select="@size"/></when>
     <otherwise><text>0</text></otherwise>
    </choose>
    <text>;</text>
   </attribute>
   <text> </text>
  </element>
 </template>

</stylesheet>

