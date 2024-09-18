#!/usr/bin/perl

use strict;
use warnings;
use CGI;

my $cgi = CGI->new;

print $cgi->header;

print << "EndOfHTML";
<!DOCTYPE html
	PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
	"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"
>
<html xmlns="http://www.w3.org/1999/xhtml" lang="en-US" xml:lang="en-US">
	<head>
		<title>Perl File Upload</title>
		<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
	</head>
	<body>
		<h1>Perl File Upload</h1>
		<form method="post" enctype="multipart/form-data">
			File: <input type="file" name="file" />
			<input type="submit" name="Submit!" value="Submit!" />
		</form>
		<hr />
EndOfHTML

if ($cgi->upload('file')) {
    my $file = $cgi->param('file');
    while (<$file>) {
        print "$_";
        print "<br />";
    }
}

print '</body></html>';
