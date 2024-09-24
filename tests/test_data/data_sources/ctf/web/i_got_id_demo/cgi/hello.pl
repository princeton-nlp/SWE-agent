#!/usr/bin/perl

use strict;
use warnings;
use CGI;

my $cgi = CGI->new;

print $cgi->header;

print "Hello World from Perl!";
