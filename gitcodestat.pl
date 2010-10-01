#!/usr/bin/perl -w
use strict;
    my @patch = @_;
    my $line;
    print "Process Patch File\n";
    # process the header
    my $header = 1;
    my $index = 0;
    my @curfile;
    my $chunk;
    my %curfile;
    my $tmp;
    foreach $line (@patch)
        chomp($line);

        if($line =~ /^diff --git (.*) (.*)/)
        {
            print "here **\n";
            if(keys(%curfile) != 0)
            {
                print "here ***\n";
                $curfile{'modified'} = $modified;
                $curfile{"added"}    = $added;
                $curfile{"deleted"}  = $deleted;
                push(@patch,%curfile);
            }
            %curfile = ();
        }
        elsif($line =~ /^index .*/)
        {

        }
        elsif($line =~/^similarity index (.*)/)
        {
            $curfile{"similarity"} = $1;
        }
        elsif($line =~/^(rename|copy) from (.*)/)
        {
            $curfile{"mode"} = $1;
            $curfile{"from"} = $2;
        }
        elsif($line =~/^(rename|copy) to (.*)/)
        {
            $curfile{"to"} = $2;
        }
        elsif($line =~/^new file mode .*/)
        {
            $curfile{"mode"} = "new";
        }
        elsif(/^--- (.*)/)
            $curfile{"orignal"} = $1;
        elsif (/^\+\+\+ (.*)/)
            $curfile{"new"} = $1;
        elsif(/^@@ -(d+),(d+) \+(d+),(d+) @@/)

        elsif(/^ .* / && $chunk != 0)
                    $modified += $chunkdel;
                    $modified += $chunkadd;
            $chunk = 0;
        elsif(/^[-](.*)/)
            $chunk = 1;
        elsif(/^[+](.*)/)
            print "line3 :$line\n";
            $chunk = 1;
        }
        else
        {
            print "line2 :$line\n";
    return %curfile;
open(TEST,"git rev-list --reverse HEAD |");

my $rev1 = <TEST>;
chomp($rev1);
while(<TEST>)
    $rev2 = $_;
    chomp($rev2);
    print "looking at COMMIT: $rev1..$rev2\n";
    open(PATCH,"git diff -M $rev1..$rev2 |") or die "failed to gif diff";
    my @patch = <PATCH>;
    close(PATCH);
    my %file;
    %file = ProcessPatchFile(@patch);
    my $key;
    my $value;
    while(($key,$value) = each (%file))
    {
        print "$key : $value\n";
    }
    $rev1 = $rev2;