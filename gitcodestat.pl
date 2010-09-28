#!/usr/bin/perl


sub ProcessPatchFile
{


}

ProcessPatchFile
{
    my @lines = $_;

    my $modified = 0;
    my $added = 0;
    my $deleted = 0;
    my $chunkadd = 0;
    my $chunkdel = 0;

    foreach $line (@lines)
    {
        #parse the patch file (first character is key)
        if(/^--- (.*)/)
        {
            $orginal=$1;
        }
        elsif (/^+++ (.*)/)
        {
            $new=$1;
        }
        elsif(/^@@ -(d+),(d+) +(d+),(d+)/)
        {
            $patchchanges = abs($2 - $4);
            $patch = 1;
        }
        elsif(/^ /)
        {
            # figure out the added, deleted, modified
            if($chunkadd != 0 && $chunkdel != 0)
            {
                if($chunkadd > $chunkdel)
                {
                    $modify += $chunkdel;
                    $added += $chunkadd - $chunkdel;
                }
                else
                {
                    $modify += $chunkadd;
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
        }
        elsif(/^-/)
        {
            $chunkdel++;

        }
        elsif(/^+/)
        {
            $chunkadd++;
        }
    }
    # catch the last chunck
    return ($orig,$new,$added,$deleted,$modified);
}


# input is a list of hashes

my $rev1 = <STDIN>;
my $rev2;

while(<STDIN>)
{
    $rev2 = <STDIN>;
    open(<PATCH>,"git diff -p $rev1..$rev2 |");
    my $patch = <PATCH>;
    close(<PATCH>);
    
    ProcessPatchFile(
    


}
