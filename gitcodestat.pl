my @totals;
    my @patch;
    @patch = @_;

    my $chunk = 0;

        if($header == 1)
            if($line =~ /^diff --git (.*) (.*)/)
                if(keys(%curfile) != 0)
                {
                    $curfile{'modified'} = $modified;
                    $curfile{"added"}    = $added;
                    $curfile{"deleted"}  = $deleted;
                    push(@totals,{%curfile});
                }
                %curfile = ();
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
            elsif($line =~ /^--- (.*)/)
            {
                $curfile{"orignal"} = $1;
            }
            elsif ($line =~ /^\+\+\+ (.*)/)
            {
                $curfile{"new"} = $1;
            }
            elsif($line =~ /^@@(.*)/)
            {
                $header = 0; # done with the header
            }
        else
            if($line =~ /^[-](.*)/)
            {
                $chunkdel++;
                $chunk = 1;
            }
            elsif($line =~ /^[+](.*)/)
                $chunkadd++;
                $chunk = 1;
            }
            else
            {
                # process the chunk stuff
                if($chunk == 1)
                    if($chunkadd != 0 && $chunkdel != 0)
                    {
                        if($chunkadd > $chunkdel)
                        {
                            $modified += $chunkdel;
                            $added += $chunkadd - $chunkdel;
                        }
                        else
                        {
                            $modified += $chunkadd;
                            $deleted += $chunkdel - $chunkadd;
                        }
                    }
                    else
                    {
                        $added += $chunkadd;
                        $deleted = $chunkdel;
                    }
                    $chunkadd = 0;
                    $chunkdel = 0;
                    $chunk = 0;
                if($line =~ /^diff/)
                    # end of the file
                    $header = 1;

                    if(keys(%curfile) != 0)
                    {
                        $curfile{'modified'} = $modified;
                        $curfile{"added"}    = $added;
                        $curfile{"deleted"}  = $deleted;
                        push(@totals,{%curfile});
                    }
                    %curfile = ();
        }
    }
    if(keys(%curfile) != 0)
    {
        # process the chunk stuff
        if($chunkadd != 0 && $chunkdel != 0)
        {
            if($chunkadd > $chunkdel)
            {
                $modified += $chunkdel;
                $added += $chunkadd - $chunkdel;
            }
                $modified += $chunkadd;
                $deleted += $chunkdel - $chunkadd;
            $added += $chunkadd;
            $deleted = $chunkdel;

        $curfile{'modified'} = $modified;
        $curfile{"added"}    = $added;
        $curfile{"deleted"}  = $deleted;
        push(@totals,{%curfile});

    ProcessPatchFile(@patch);
    $totals[-1]{"ref1"} = $rev1;
    $totals[-1]{"ref2"} = $rev2;
    $rev1 = $rev2;
}


my $key;
my $href;

for $href ( @totals )
{
    print "\nnew commit\n";

    for $key ( keys  %$href )
        print "$key : $href->{$key}\n"