dir = File.dirname(__FILE__)
$ext_path = "/++resource++extjs/"
ext_filesystem = `python -c "import pkg_resources; import zenoss.extjs; print zenoss.extjs.__path__[0]"`.strip
load File.join(ext_filesystem, 'src', 'resources', 'themes')

#line_comments = false
sass_path = dir
css_path = File.join(dir, "..", "css")
images_dir = File.join(dir, "..", "img")
javascripts_dir = File.join(dir, "..", 'js')

http_path = "/"
output_style = :normal
environment = :production
#development
