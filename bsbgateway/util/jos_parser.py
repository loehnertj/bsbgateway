
##############################################################################
#
#    Copyright (C) Johannes Loehnert, 2013-2015
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import re

__all__ = [
            "Token", "AstNode", "ParserContext", "StackTrace", 
            "seq", "multiple", "optional", "anyof",
            "generate_lexer", "re", "generate_parser",
        ]
class Token(object):
    ntype=0
    content=None
    srcoffset = 0
    def __init__(o, ntype, content=None, srcoffset=0):
        o.ntype = ntype
        o.content = content
        o.srcoffset = srcoffset

    def __unicode__(o):
        if not o.content:
            return o.ntype
        content = o.content
        if not isinstance(content, unicode):
            content = unicode(content)
        if len(content)> 40: 
            content = content[:37] + u"..."
        return unicode(o.ntype) + u"<" + content.replace("\n", "\n        ") + u">"

    def __str__(o):
        if not o.content:
            return o.ntype
        content = o.content
        if not isinstance(content, str):
            content = str(content) # may throw encode error!!!
        if len(content)> 40: 
            content = content[:37] + "..."
        return o.ntype + "<" + content.replace("\n", "\n        ") + ">"
    __repr__ = __str__


    def __call__(o):
        return o.content

class AstNode:
    """represents a node of the abstract syntax tree
    sequence is a list of the children. Its items
    can be Tokens and AstNodes, mixing is allowed.
    Take care: a single Token object is a valid tree!!
    The tree structure will match the given grammar.
    """
    ntype = ""
    _children = None
    def __init__(o, ntype, children):
        o.ntype = ntype
        o._children = children
    def __str__(o):
        s = o.ntype
        for c in o._children:
            s = s + "\n" + str(c).replace("\n", "\n    ")
        return s
    def __unicode__(o):
        s = unicode(o.ntype)
        for c in o._children:
            s = s + u"\n" + unicode(c).replace("\n", "\n    ")
        return s
    def __getattr__(o, ntype):
        """gets the child node(s) having the given ntype. 
        Returns list of children that matches."""
        result = []
        for c in o._children:
            if c.ntype == ntype:
                result.append(c)
        return result
    def __iter__(o):
        """iterates over the children of this node."""
        return o._children.__iter__()
    def __call__(o):
        """return token content of this subtree.
        The subtree must contain 0 or 1 token, multiple tokens cause an Exception.
        Returns token.content (None if no token is there)."""
        result = [c() for c in o._children]
        result = [x for x in result if x is not None]
        if len(result)>1:
            raise ValueError("More than one token in subtree '%s'"%o.ntype)

        if len(result)==0: return None
        return result[0]
    def __getitem__(o, key):
        if isinstance(key, basestring):
            l = o.__getattr__(key)
            if len(l) > 1: raise ValueError("more than one %s child"%key)
            if len(l)==0: return None
            return l[0]
        else:
            return o._children[key]


    content = property(__call__)



class ParserContext:
    def __init__(o, tokens, ruleset):
        o.tokens = tokens
        o.ruleset = ruleset.copy()
        o.stack_trace = None
        o.stack = []
    def push(o, symbol):
        '''processor should push HIS OWN name before calling subprocessors, and .pop() afterwards.'''
        o.stack.append(symbol)
    def pop(o):
        o.stack.pop()
    def mktrace(o, symbol, errdescription="", reached_position=-1):
        """create a stack trace and remember it if a bigger position was reached."""
        trace = StackTrace(o.stack+[symbol], errdescription, reached_position)
        # remember the trace if there is none remembered, if it reached longer than the last one,
        # or if it extends the last remembered one.
        if o.stack_trace is None \
                or o.stack_trace.reached_position < trace.reached_position:
            o.stack_trace = trace
        return trace

class StackTrace:
    stack = []
    reached_position =-1
    errdescription = ""
    def __init__(o, stack, errdescription="", reached_position=-1):
        o.stack = stack[:]
        o.errdescription = errdescription
        o.reached_position = reached_position
    def __str__(o):
        return " ".join(o.stack) + " : '" + o.errdescription + "' (@token %d"%o.reached_position + ")"


def _convert(args):
    """reads the given list and replaces all strings with the corresponding _expect processor.
    """
    processors = list()
    for processor in args:
        # replace strings by the '_expect' processor.
        if isinstance(processor, basestring):
            processor = _expect(processor)
        processors.append(processor)
    return processors

# Processors: ==========================================================
# each of those functions returns a processor for the token stream.
#def process(pcontext, position):
#   trys to apply itself onto the tokens, if needed branches to another rule.
#   it starts at position (index into tokens).
#       Returns (partlist, new_position):
#       partlist := LIST of AstNodes and Tokens
#           StackTrace if not applicable. 
#       new_position: where further parsing must continue

def _expect(text):
    """Expect processor: if text is lowercase, expect something matching that rule.
    if text is not lowercase, expect a token with that ntype.
    You do not need to use it directly. All strings given as argument to another processor are directly matched.
    """
    if text != text.lower():
        # expect that particular TOKEN
        def process(pcontext, position):
            tokens = pcontext.tokens
            if len(tokens) > position:
                token = tokens[position]
            else:
                # after end of stream there comes an infinite amount of EOF tokens.
                token = Token("EOF", None)
            if token.ntype == text:
                return [token], position+1
            else:
                return pcontext.mktrace("expect", errdescription="expected %s token"%text, reached_position=position), position
    else:
        # try whether the RULE applies
        def process(pcontext, position):
            pcontext.push("<%s>"%text)
            result, new_position = _try_rule(pcontext, position, text)
            pcontext.pop()
            if isinstance(result, StackTrace):
                return result, position
            else:
                return [result], new_position
    return process

def seq(*args):
    """sequence processor: match the full sequence given as arguments."""
    processors = _convert(args)
    def process(pcontext, position):
        result = []
        start_position = position
        for processor in processors:
            subresult, position = processor(pcontext, position)
            if isinstance(subresult, StackTrace):
                # parsing failed further down.
                # exception here: pass Stacktrace directly!
                return subresult, start_position
            else:
                # append returned list to my result
                result += subresult
        #success
        return result, position
    return process

def multiple(*args):
    """multiple processor: match the sequence given as arguments n times (n>=0).
    """
    subseq = seq(*args)
    def process(pcontext, position):
        result = []
        while True:
            pcontext.push("multiple")
            subresult, new_position = subseq(pcontext, position)
            pcontext.pop()
            if isinstance(subresult, StackTrace):
                # ignore trace and return what you got so far
                break;
            # detect and break endless loop
            if len(subresult) == 0:
                subresult = pcontext.mktrace("multiple", errdescription="endless loop detected", reached_position = position)
                break;
            result += subresult
            position = new_position
        return result, position
    return process

def optional(*args):
    """optional processor: match the full sequence given as argument, or empty list"""
    subseq = seq(*args)
    def process(pcontext, position):
        pcontext.push("optional")
        subresult, new_position = subseq(pcontext, position)
        pcontext.pop()
        # only thing we have to do is convert StackTrace (no match) into a valid match.
        if isinstance(subresult, StackTrace):
            return [], position
        else:
            return subresult, new_position
    return process

def anyof(*args):
    """anyof processor: try the given processors in turn, return the first match.
    for alternative sequences, wrap them in seq(...).
    """
    processors = _convert(args)
    if len(processors)==0:
        raise ArgumentError, "at least one alternative must be given to anyof"
    def process(pcontext, position):
        for processor in processors:
            pcontext.push("anyof")
            result, new_position = processor(pcontext, position)
            pcontext.pop()
            if not isinstance(result, StackTrace):
                return result, new_position
        # nothing matched
        return pcontext.mktrace("anyof", "no alternative matched", position), position
    return process

# END of processor generators! ============================

def _try_rule(pcontext, position, rulename):
    """ takes a list of Tokens, the ruleset, and the name of the subtree rule.
    Returns the AST (tree of AstNodes and/or tokens), or StackTrace if parsing failed.
    """
    processor = pcontext.ruleset[rulename]
    result, new_position = processor(pcontext, position)
    if isinstance(result, StackTrace):
        return result, position
    else:
        return AstNode(rulename, result), new_position


def generate_lexer(symbols, re_flags):
    """generates a lexer function for the given symbol set.
    The symbol set is a list: ["SYMBOL1", "regex1", "SYMBOL2", "regex2", (...)].
    Internally, re.Scanner is used. Look up the re module docs for regexp syntax.

    Applied to a source string, the lexer function returns a list of Tokens, ie.
    Token objects.

    Use the empty string "" as symbol for symbols to be ignored (e.g. whitespace).
    No Tokens are generated for those.

    Mark the content of the token by a capture group in the regexp. If there is
    a named group "content", it is set as Token content. If not, the first
    capture group is set as Token content. If there are no capture groups,
    content will be None.

    Known Bug: the first regex will always have a capture group, by default the 
    whole match. If you want a token without content, put () at the end to
    make the first capture group an empty string.
    """

    # factory that returns a specific token-generator.
    def factory(ntype, has_value):
        def mktoken(regex, match):
            if has_value:
                # From the construction of the regex, the group having the
                # index of the named group +1 is our value.
                content = match.group(regex.groupindex[ntype] + 1)
            else:
                content = None
            t = Token(ntype, content, match.start())
            return t
        return mktoken

    regexs = []
    symnames = []
    funcs = {}
    for sym, regex in zip(symbols[::2], symbols[1::2]):
        if sym == "":
            regexs.append("r(%s)"%(sym))
        else:
            symnames.append(sym)
            regexs.append(r"(?P<%s>%s)"%(sym, regex))
            # check if the regex defines groups i.e. delivers a value
            p = re.compile(regex)
            funcs[sym] = factory(sym, (p.groups>0))

    regex = re.compile("|".join(regexs), re_flags)
    def lexer(text):
        tokens = []
        lastpos = 0
        for match in regex.finditer(text):
            # find matched symbol
            groups = match.groupdict()
            for sym in symnames:
                if groups[sym]:
                    tokens.append(funcs[sym](regex, match))
                    break;
            lastpos = match.end()
        return tokens, text[lastpos:]
    return lexer





def generate_parser(ruleset, entrypoint=""):
    """generates a parser for the given grammar (ruleset).
    The ruleset must be a dictionary with:
        string keys (rulenames), which MUST be lowercase
        processor or string values.
        values:
            processors are callbacks built by nesting the functions seq, multiple, optional, anyof.
            string values match either another rule (if lowercase) or one token (if not lowercase).
                In the latter case, the string value is compared against the Token.ntype.
        by default, the rule "" (empty string as key) is used as entrypoint. You can give another
        entrypoint for testing parts of the grammar.

    """
    rules = ruleset.copy()
    # convert string values into _expect
    for key in rules.keys():
        if isinstance(rules[key], basestring):
            rules[key] = _expect(rules[key])
    def parse(tokens):
        """ takes a list of Tokens.
        Returns (tree, pcontext) -
            tree: the AST (tree of AstNodes and/or tokens), or None if parsing failed.
                NOTE that a single Token is also a valid tree.
            pcontext: final state of parsing contest (for error location)
            .stack_trace: a StackTrace object if parsing failed
                .stack_trace.stack: list of called operators
                .stack_trace.reached_position: where the parser failed to continue
                use it to validate if everything was read, or for error messages.
        """
        pcontext = ParserContext(tokens, rules)
        result, end_position = _try_rule(pcontext, 0, "")
        if isinstance(result, StackTrace):
            result = None
            print pcontext.stack_trace
        else:
            pcontext.stack_trace = None
        return result, pcontext
    return parse
