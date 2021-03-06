#!/usr/bin/env python
'''
disSECt: contract mining in SEC
'''
import argcomplete
import argparse
import codecs
from training import watershed
import build_training_data
import findimagefiles
import score_filings
import tempfile
import subprocess
import sys

class Runner:
    
    def __init__(self, cmdargs, **kwargs):
        self.args = cmdargs

    def run(self, *args, **kwargs):
        pass

class WatershedRunner(Runner):

    def run(self):
        watershed.run(pos_dirs=self.args.pos_dir, neg_dirs=self.args.neg_dir, threshold=self.args.threshold, ngram_max=self.args.ngram_max, outfn=self.args.outfile)

class BuildTrainingDataRunner(Runner):

    def run(self):
        build_training_data.run(self.args)

class MRRunner(Runner):
    standard_options = ['-r', 'local', '--jobconf', 'mapred.map.tasks=10']
    
    def mr_args(self):
        return self.input_file() + self.standard_options

    def input_file(self):
        dirname = args.source_directory
        if not dirname:
            return []
        fh = tempfile.NamedTemporaryFile(delete=False)
        fn_search = ['find', args.source_directory, '-type', 'f'] #, '-name', '*pdf']
        fh.write(subprocess.check_output(fn_search))
        return [fh.name]

    def run(self):
        job = self.MRCLASS(args=self.mr_args())
        if self.args.outfile:
            output = codecs.open(self.args.outfile, 'w', 'utf-8')
        else:
            output = sys.stdout
        with job.make_runner() as runner:
            runner.run()
            for line in runner.stream_output():
                output.write(line)

class FindImageFiles(MRRunner):
    MRCLASS=findimagefiles.ImagePDFs


    def mr_args(self):
        options = ['-r', 'local', '--jobconf', 'mapred.map.tasks=2']
        return self.input_file() + options


class ScoreRunner(MRRunner):
    MRCLASS=score_filings.MRScoreFiles

    def mr_args(self):
        assert self.args.watershed and self.args.stopwords 
        customargs = ['--watershed', '/tmp/watershed_list.txt', '--stopwords', '/tmp/stopwords.txt']
        if self.args.pdf_input:
            customargs.append('--pdf_input')
        return self.standard_options + customargs

TASKS = {
    'download_data': '',
    'build_training_data': BuildTrainingDataRunner,
    'build_watershed': WatershedRunner,
    'score_documents': ScoreRunner,
    'find_image_files': FindImageFiles,
    }

SOURCES = ['edgar', 'sedar', 'asx']
INDUSTRIES = ['oil', 'mining']

def add_shared_args(parser):
    parser.add_argument('--industry', choices=INDUSTRIES, help="which industry sector should we look at?")
    parser.add_argument('--source', choices=SOURCES, default=None, help="which set of filings do we care about?")
    parser.add_argument('--last_year', type=int, default=2014, help="the most recent year (inclusive) to work on")
    parser.add_argument('--first_year', type=int, default=2000, help="the earliest year (inclusive) to work on")
    parser.add_argument('--outfile', help="where to put output")
    return parser


def build_argparser(parser=None):
    parser = parser or argparse.ArgumentParser()
    parser.add_argument('action', choices=TASKS.keys(), help="which part of the process to run. Required")

    general_group = parser.add_argument_group('general options')
    general_group = add_shared_args(general_group)
    
    watershed_group = parser.add_argument_group('build_watershed_list')
    watershed_group = watershed.build_parser(watershed_group)

    build_training_group = parser.add_argument_group('build_training_data', description='also supply pos_dir here')
    build_training_group = build_training_data.build_parser(build_training_group)

    mapreduce_group = parser.add_argument_group('mapreduce', description='Options common to running mapreduce jobs (scoring, watershed, etc)')
    mapreduce_group.add_argument('--source-directory', help='Directory containing input files for the job. If not supplied, use stdin (expecting a list of files)')

    mapreduce_group.add_argument('--watershed', help='Full path to file containing watershed list')
    mapreduce_group.add_argument('--stopwords', help='Full path to file containing watershed list')
    mapreduce_group.add_argument('--pdf_input', help='Expect input files in PDF format; extract text from them before processing', action="store_true", default=False)


    argcomplete.autocomplete(parser)
    return parser

def check_args(args, parser):
    '''
    Ensure the options provided are coherent
    If not, stop running
    '''
    return True # XXX Writeme

if __name__ == '__main__':
    parser = build_argparser()
    args = parser.parse_args()
    check_args(args, parser)
    runner = TASKS[args.action](args)
    runner.run()

