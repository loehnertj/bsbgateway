# BsbGateway - Commandline Interface

The commandline interface allows you to query the list of fields, retrieve and set values.


## Command list

The following commands are defined:

 * `help [<cmd>]` - help on specific command, or list of commands.
 * `quit` - Stops BsbGateway.
 * `get <field>` - request and print value of field with ID `<field>` once.
   The ID is the value as seen on the standard LCD display. 
 * `set <field> <value>[!]` - set value of field with ID `<field>`. See [below](#setting-values).
 * `list [#][<text>][+]`: list field groups. See [below](#listing-fields).
 * `info <id>[ <id>...]`: print field descriptions for the given field ids.
 * `dump [<expr>]` - dump received data matching the filter. See [below](#sniffing-the-bus).
 
## Listing fields

Fields in Bsbgateway are sorted into groups. Each field belongs to exactly one group.
Each group has an ID number which is the common prefix of the contained fields.
The groups correspond to the menus in the LCD panel.

The `list` command lists groups and fields:

 * `list` lists all known *groups* (captions only).
 * `list #<text>` lists all *groups* containing the text. If only a single group matches,
   its fields are listed as well, otherwise only the group names.
 * `list <text>` lists all *fields* whose name contains the text.
 * `list+` or `list #<text>+` forces expanded view, i.e. the contained fields are printed
   for all groups matching the text.

The `info` command gives detailed information about one or more fields.
    
    
## Setting values
    
`set <field> <value>[!]` - sets value of field with ID `<field>`.
The ID is the value as seen on the standard LCD display.

Depending of the type of the field, the value must be entered as follows:

 * numeric fields: as usual, e.g. `0`, `1.1`, `-5`
 * time: as hh:mm e.g. `08:30`
 * choice: index e.g. `2` (you can get the list of choices via `info <field>`)
 * to reset a field, use `--` as value. The field must allow Null values.
 
By default, you can only set "writable" fields, and the value is bound checked.

You can use  `!` after the value to disable validation. This will send
anything as long as it can be converted into bytes. **Be extremely careful.
You might DESTROY your device with this. USE AT YOUR OWN RISK.**


## Sniffing the bus

`dump [<expr>]` dumps all telegrams matching the filter defined by `<expr>`. This
looks at everything going over the bus.

`<expr>` is a python expression(*). In the expression you can use the variables:
 * `src` - source bus address ex. `src=10`
 * `dst` - destination bus address ex. `dst=0`
 * `field` - disp id of field ex. `field=8510`
 * `fieldhex` - hex (bus visible) id of field ex. `fieldhex=0x493d052a`
 * `type` - ret, get, set, ack, inf ex. `type=ack`
    
The result of the expression must be True or False. (*) To make life easier, you can
compare with single `=`, and no quotes are required around the type names (e.g. "ack").

Special cases:

 * `dump off`: dump nothing (the startup setting).
 * `dump on`: dump everything that goes over the bus.
 * `dump` without argument, toggle between on and off.
            
Some examples:
 * `dump type=ret` dumps all return telegrams (answer to get).
 * `dump field=8510` dumps all telegrams concerning that field.
 * `dump dst=10 or src=10` dumps all telegrams from or to address 10.
