# Nothing is required in this __init__.py, but it is an excellent place to do
# many things in a ZenPack.
#
# The example below which is commented out by default creates a custom subclass
# of the ZenPack class. This allows you to define custom installation and
# removal routines for your ZenPack. If you don't need this kind of flexibility
# you should leave the section commented out and let the standard ZenPack
# class be used.
#
# Code included in the global scope of this file will be executed at startup
# in any Zope client. This includes Zope itself (the web interface) and zenhub.
# This makes this the perfect place to alter lower-level stock behavior
# through monkey-patching.

# import Globals
#
# from Products.ZenModel.ZenPack import ZenPack as ZenPackBase
# from Products.ZenUtils.Utils import unused
#
# unused(Globals)
#
#
# class ZenPack(ZenPackBase):
#
#     # All zProperties defined here will automatically be created when the
#     # ZenPack is installed.
#     packZProperties = [
#         ('zExampleString', 'default value', 'string'),
#         ('zExampleInt', 411, 'int'),
#         ('zExamplePassword', 'notsecure', 'password'),
#         ]
#     # Provides information about a property such as the category, label and description
#     packZProperties_data = {
#         'zExampleString'= {
#                 'category': 'Example',
#                 'label': 'An Example String',
#                 'description': 'A very useful description about how we use zExampleString.'
#         }
#     }

#     def install(self, dmd):
#         ZenPackBase.install(self, dmd)
#
#         # Put your customer installation logic here.
#         pass
#
#     def remove(self, dmd, leaveObjects=False):
#         if not leaveObjects:
#             # When a ZenPack is removed the remove method will be called with
#             # leaveObjects set to False. This means that you likely want to
#             # make sure that leaveObjects is set to false before executing
#             # your custom removal code.
#             pass
#
#         ZenPackBase.remove(self, dmd, leaveObjects=leaveObjects)
