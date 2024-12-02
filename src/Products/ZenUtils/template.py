##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


class SpecialDict(object):
    def __init__(self, data):
        self_dict = object.__getattribute__(self, '__dict__')
        self_dict.update(data)

    def __getattr__(self, item):
        self_dict = object.__getattribute__(self, '__dict__')
        try:
            return self_dict[item]
        except KeyError:
            return None

class Template(object):
    def __init__(self, template_body):
        self.template_body = template_body
    
    def fill(self, **kwargs):
        def dict_to_obj(d):
            for k,v in d.iteritems():
                if isinstance(v, dict):
                    d[k] = dict_to_obj(v)
            return SpecialDict(d)
        
        return self.template_body.format(**dict_to_obj(kwargs).__dict__)
