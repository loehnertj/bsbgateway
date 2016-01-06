# BsbGateway - Web Interface

The web interface can be reached via any browser at the configured port. You need to know the IP address of the computer where BsbGateway is running on. In your browser, enter the address like: `http://192.168.1.123:8081`. You should see the index page listing the available groups.

No authentication or user levels are implemented so far. **Javascript must be enabled.**

Usage of the web interface should be straightforward. Below follows a list of defined URLs. For automated getting/setting of values, have a look at `field-0815.value` and `field-0815 (POST)`.

## Index

Path: `/` - yields the index page as html.

## Group

Path: `/group-<number>` e.g. `group-1600` - displays the given group of fields.

Note that the fields are loaded with delay (0.5s for each field) in order to not block the BSB bus with requests.

If `...` is displayed after each field permanently, most likely you need to enable Javascript.

## Field

Multiple subqueries exist. Replace `<number>` with the 4-digit field number in each one. **Note that each query causes a GET telegram to be sent over the bus. No rate limiting is done.**

 * `/field-<number>`, e.g. `/field-1620` - displays the field as a standalone page.

 * `/field-<number>.fragment` - returns only the body i.e. everything in the <body> tag.
 
 * `/field-<number>.widget` - returns only the value part. In case of a readonly field, this is the formatted value; in case of a readwrite field, the HTML form.
 
 * `field-<number>.value` - returns the current value as JSON. Returns a json object with the following keys:
   * `disp_id`: The field id (that has been given)
   * `disp_name`: The field's display name, utf8-encoded
   * `timestamp`: unix timestamp when the value was queried
   * `value`: The value - int, float or list.

The structure of `value` depends on the field type:
  * Unknown type: list of byte values, the raw payload of the return telegram.
  * int8: integer value
  * int16, temperature: float value
  * time: list of two values `[<hour>, <minute>]`
  * choice: list of two values `[<index>, <text>]` with `index` being the numeric index of the choice and `text` its cleartext representation.

To **set** a value, `POST` to `/field-<number>`. Depending on the value, you need to supply either a single parameter `value` or two parameters `hour` and `minute`.

 * For a time field, give `hour` and `minute` as integers.
 * For all other types, give `value`: a float number in the usual notation (`.` as decimal, `e+01` is allowed).
 * To set a nullable field to NULL, `POST` without any parameters.
 
Only valid values can be set. You cannot override validation from the web interface (as opposed to the [Commandline Interface](cmdline.md) ).