#!/usr/bin/env perl

use strict;
use warnings;

use CGI;

my $cgi = CGI->new;

print $cgi->header('text/html');

print << "EndOfHTML";
<!DOCTYPE html
	PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
	"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"
>
<html xmlns="http://www.w3.org/1999/xhtml" lang="en-US" xml:lang="en-US">
	<head>
		<title>A Simple CGI Page</title>
		<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
	</head>
	<body>
		<h1>A Simple CGI Page</h1>
		<form method="post" enctype="multipart/form-data">
			Name: <input type="text" name="name"  /><br />
			Age: <input type="text" name="age"  /><p />
			<input type="submit" name="Submit!" value="Submit!" />
		</form>
		<hr />
EndOfHTML

if ( my $name = $cgi->param('name') ) {
    print "Your name is $name.<br />";
}

if ( my $age = $cgi->param('age') ) {
    print "You are $age years old.";
}

print '</body></html>';
