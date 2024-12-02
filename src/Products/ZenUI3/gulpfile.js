var gulp = require('gulp'),
    concat = require('gulp-concat'),
    sequence = require("run-sequence"),
    uglify = require('gulp-uglify'),
    jshint = require("gulp-jshint"),
    fs = require('fs');

gulp.task('build', function(){

    // Read all the files from zenoss.jsb2 into an array
    var manifest = JSON.parse(fs.readFileSync('browser/zenoss.jsb2', 'utf8')),
        fileList = manifest.pkgs[0].fileIncludes, i, files=[];
    for (i=0; i<fileList.length; i++ ){
        files.push(fileList[i].path + fileList[i].text);
        files[i] = files[i].replace("resources/js/", "");
    }

    // concat the files
    gulp.src(files)
        .pipe(concat('zenoss-compiled.js'))
        .pipe(uglify())
        .pipe(gulp.dest('browser/resources/js/deploy'));
});


gulp.task("lint", function(){
    return gulp.src("browser/resources/js/zenoss/*")
        .pipe(jshint())
        .pipe(jshint.reporter("jshint-stylish"))
        .pipe(jshint.reporter("fail"));
});

gulp.task("default", function() {
    sequence("lint", "build", function(){
    });
});
