### How to use the icons

To see the whole list of available icons, open the **icon-list.html** file in your browser. It
will display all available icons with their class name next to them. To include an icon in your
HTML, just add that class name to an *i* tag, e.g.:

    <i class="icon-mail"></i>

Or, in jade:

    i.icon-mail

To change the color or size of your icon, set the font-size or color style properties on the
parent element of the icon.

### How to add or remove icons in the icon set

If you want to add or remove icons from the available set, go to [fontello](http://fontello.com)
and click **Import config** from the action menu. When prompted, select to upload the
[config.json](config.json) file in this directory. It will select all of the current icons in
our custom set. Click on included ones to remove them from the set, or click on others to add
them to the set. When done, download the set as a zip file and replace the existing
[css/fontello.css](css/fontello.css) and all of the files in the [font](font) directory with
the ones from the downloaded archive, as well as the [config.json](config.json) file.

> **Important**: Only add icons from sets published under the [SIL](http://scripts.sil.org/OFL)
license.
