# Copyright (c) 2008, Brandon Martin-Anderson
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Servable project nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from wsgiref.simple_server import make_server
from types import *
import re
import cgi
import traceback
from urlparse import urlparse

try:
    from simplejson import loads as json_loads
    #from simplejson import dumps as json_dumps
except ImportError:
    from json import loads as json_loads
    #from json import dumps as json_dumps

            
def function_arg_names(func):
    return func.func_code.co_varnames[0:func.func_code.co_argcount]
    
def method_arg_names(meth):
    return function_arg_names(meth)[1:]
    
def method_name(meth):
    return meth.func_name
    
def method_path(meth):
    if hasattr(meth, 'path'):
        return meth.path
    else:
        return "/"+method_name(meth)+"$"

def methods(cls):
    for name in dir(cls):
        attr = getattr(cls, name)
        if type(attr) == UnboundMethodType:
            yield attr
            
def xstr(arg):
    if arg is None:
        return ""
    else:
        return arg.encode('utf8')

class Servable:
    DEFAULT_MIME = "text/plain"        
    
    def patterns(self):
        """returns list of (path,argnames,method)"""
        
        for method in methods(self.__class__):
            if method_name(method)[0]!='_' and not(hasattr(method,'serve') and method.serve==False):
                yield re.compile(method_path(method)), method_arg_names(method), method
    patterns.serve = False

    def wsgi_app(self):
        """returns a wsgi app which exposes this object as a webservice"""
        
        def myapp(environ, start_response):
            
            path_info = environ['PATH_INFO']
            query_string = environ['QUERY_STRING']
            
            if not hasattr(self, 'pattern_cache'):
                self.pattern_cache = [(pth, args, pfunc) for pth, args, pfunc in self.patterns()]
            
            for ppath, pargs, pfunc in self.pattern_cache:
                if ppath.match(path_info):
                    
                    args = cgi.parse_qs(query_string)
                    args = dict( [(k,v[0]) for k,v in args.iteritems()] )
                        
                    try:
                        #use simplejson to coerce args to native types
                        #don't attempt to convert an arg 'jsoncallback'; just ignore it.
                        arglist = []
                        for k,v in args.iteritems():
                            if k=="jsoncallback":
                                arglist.append( (k,v) )
                            elif k != "_":
                                arglist.append( (k,json_loads(v)) )
                        args = dict( arglist )
                        
                        #try:
                        rr = xstr( pfunc(self,**args) )
                        #except TypeError:
                        #    problem = "Arguments different than %s"%str(pargs)
                        #    start_response('500 Internal Error', [('Content-type', 'text/plain'),('Content-Length', str(len(problem)))])
                        #    return [problem]
            
                        if hasattr(pfunc, 'mime'):
                            mime = pfunc.mime
                        else:
                            mime = self.DEFAULT_MIME
                            
                        start_response('200 OK', [('Content-type', mime),('Content-Length', str(len(rr)))])
                        return [rr]
                    except:
                        problem = traceback.format_exc()
                        start_response('500 Internal Error', [('Content-type', 'text/plain'),('Content-Length', str(len(problem)))])
                        return [problem]
                        
            # no match:
            problem = "No method corresponds to path '%s'"%environ['PATH_INFO']
            start_response('404 Not Found', [('Content-type', 'text/plain'),('Content-Length', str(len(problem)))])
            return [problem]
            
        return myapp
    wsgi_app.serve = False
        
    def run_test_server(self, port=8080):
        print "starting HTTP server"
        httpd = make_server('', port, self.wsgi_app())
        httpd.serve_forever()
    run_test_server.serve = False
        
    def usage(self):
        ret = ["<?xml version='1.0'?><api>"]
        for ppath, pargs, pfunc in self.patterns():
            ret.append("<method><path>%s</path>" % ppath.pattern)
            if pfunc.__doc__:
                ret.append("<doc>%s</doc>"%pfunc.__doc__)
            ret.append("<params>")
            if pargs:
                for p in pargs:
                    ret.append("<param>%s</param>" %p)
            ret.append("</params></method>")
        ret.append("</api>")
        return "".join(ret)
    usage.path="/$"
    usage.mime = "text/xml"
    usage.serve = True
