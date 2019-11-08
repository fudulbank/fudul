var gulp = require('gulp');
var pipeline = require('readable-stream').pipeline;
var rename = require('gulp-rename');
var sourcemaps = require('gulp-sourcemaps');
var uglify = require('gulp-uglify');

function compress () {
    var options = {mangle: {toplevel: true,
			    reserved: ['$','g','initializeMnemonicInteractions']},
		   output: {comments: 'some'}};
    options.mangle.properties = {regex: /^__/}
		  
  return pipeline(
        gulp.src('exams/static/js/show_session.js'),
        sourcemaps.init(),
        uglify(options),
        rename({ extname: '.min.js' }),
        sourcemaps.write('.', {includeContent: false}),
        gulp.dest('exams/static/js/')
  );
}

function watch () {
    gulp.watch(['exams/static/js/show_session.js'], compress);
}

gulp.task('compress', compress);
gulp.task("watch", watch);

gulp.task("default",  gulp.series("compress", "watch"));
