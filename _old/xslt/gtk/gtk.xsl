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
  <element name="interface" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
   <element name="requires" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="lib">gtk+</attribute>
    <attribute name="version">3.8</attribute>
   </element>
   <element name="object" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="class">GtkWindow</attribute>
    <attribute name="id">main_window</attribute>
    <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
     <attribute name="name">can_focus</attribute>
     <text>False</text>
    </element>
    <element name="signal" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
     <attribute name="name">delete-event</attribute>
     <attribute name="handler">on_window_delete_event</attribute>
     <attribute name="swapped">no</attribute>
    </element>
    <element name="signal" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
     <attribute name="name">destroy</attribute>
     <attribute name="handler">on_window_destroy</attribute>
     <attribute name="swapped">no</attribute>
    </element>
    <element name="child" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
     <apply-templates select="a:vbox|a:hbox"/>
    </element>
   </element>
  </element>
 </template>

 <!-- template match="f:*">
  <copy-of select="."/>
 </template -->

 <template match="a:hbox">
  <element name="object" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
   <attribute name="class">GtkBox</attribute>
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">visible</attribute>
    <text>True</text>
   </element>
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">can_focus</attribute>
    <text>False</text>
   </element>
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">orientation</attribute>
    <text>horizontal</text>
   </element>
   <for-each select="*">
    <element name="child" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
     <apply-templates select="."/>
    </element>
   </for-each>
  </element>
 </template>

 <template match="a:vbox">
  <element name="object" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
   <attribute name="class">GtkBox</attribute>
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">visible</attribute>
    <text>True</text>
   </element>
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">can_focus</attribute>
    <text>False</text>
   </element>
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">orientation</attribute>
    <text>vertical</text>
   </element>
   <for-each select="*">
    <element name="child" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
     <apply-templates select="."/>
    </element>
   </for-each>
  </element>
 </template>

 <template match="a:space">
  <element name="object" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
   <attribute name="class">GtkLabel</attribute>
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">visible</attribute>
    <text>True</text>
   </element>
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">can_focus</attribute>
    <text>False</text>
   </element>
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">label</attribute>
    <attribute name="translatable">no</attribute>
    <text></text>
   </element>
  </element>
  <element name="object" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">expand</attribute>
    <text>True</text>
   </element>
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">fill</attribute>
    <text>True</text>
   </element>
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">position</attribute>
    <value-of select="position()"/>
   </element>
  </element>
 </template>

 <template match="f:*">
  <element name="object" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
   <attribute name="class">XForms</attribute>
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">visible</attribute>
    <text>True</text>
   </element>
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">can_focus</attribute>
    <text>False</text>
   </element>
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">label</attribute>
    <attribute name="translatable">no</attribute>
    <text></text>
   </element>
  </element>
  <element name="object" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">expand</attribute>
    <text>True</text>
   </element>
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">fill</attribute>
    <text>True</text>
   </element>
   <element name="property" namespace="https://git.gnome.org/browse/gtk+/tree/gtk/gtkbuilder.rnc">
    <attribute name="name">position</attribute>
    <value-of select="position()"/>
   </element>
  </element>
 </template>


</stylesheet>

