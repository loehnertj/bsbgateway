# BsbGateway - Logging

In the config file, you can configure fields for logging. For each field the log interval is given.

Logging is rasterized so that the (unix) timestamp for each log point is a multiple of the interval. That means that log data points are evenly rasterized, even if BsbGateway is stopped and restarted. Also, if 24h / interval can be divided without remainder, the log times will be the same for each day.

Each logger writes to a file named `<disp_id>.trace` in the configured trace directory. E.g. field 8510 would be logged to `8510.trace`. **The trace files are only ever appended to. Existing data cannot be overwritten.**

The trace format is described below. You can use `trace/load_trace.py` to load trace files into numpy arrays (requires `numpy`):

    from load_trace import Trace
    t = Trace('8510.trace')
    print t.index, t.data
    
`t.index` gives the log times as `datetime.datetime` objects. `t.data` contains the values. Both are 1d arrays.
For further information, look at `Trace`'s docstring.


## Triggers

You can define triggers. I.e. something happens when the trigger condition applies. Currently there are two types of trigger: `rising_edge` (Value climbs above a threshold) or `falling_edge` (Value below threshold). The only available action so far is to send an email. The sender credentials and recipient address must be given in `config.py`.

When a trigger fires, it cannot be triggered again in the next 6 hours.


## Trace files

The trace files are ASCII files with a primitive Run-length-encoding. The format is made so that stuff can be appended without worrying about what is already there.
In short:

 * Lines starting with `:` contain metadata: `:<key> <value>`. Each key can appear multiple times. e.g. interval can change inbetween.
 * Empty lines are skipped.
 * Value lines contain the value at the beginning, and a varying number of tilde (`~`) signs. Each tilde means "same value repeats".
 * There are no timestamps. The values are rasterized according to the interval. If gaps or interval changes occur, a `:time` metadata line gives the new timestamp for the next value.

Example:

    :disp_id 8007
    :fieldname Status Solar
    :interval 5
    :time 1450906640
    :dtype choice
    1~~
    2~
    1~~~~~~~
    :interval 5
    :time 1451118720
    :dtype choice
    1~~~~~~~~
    2~
    1~~~~
