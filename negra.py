from nltk.corpus.reader.api import CorpusReader, SyntaxCorpusReader
from nltk.corpus.reader.util import read_regexp_block, StreamBackedCorpusView, concat
from nltk import Tree
import re

BOS = re.compile("^#BOS.*\n")
EOS = re.compile("^#EOS")
WORD, LEMMA, TAG, MORPH, FUNC, PARENT = range(6)

class NegraCorpusReader(SyntaxCorpusReader):
	def __init__(self, root, fileids, encoding=None, n=6, headorder=False, headfinal=False, reverse=False):
		""" n=6 for files with 6 columns, n=5 for files with 5 columns (no lemmas)
			headfinal: whether to put the head in final or in frontal position
			reverse: the head is made final/frontal by reversing everything before or after the head. 
				when true, the side on which the head is will be the reversed side"""
		if n == 5: self.d = 1
		else: self.d = 0
		self.headorder, self.headfinal, self.reverse = headorder, headfinal, reverse
		CorpusReader.__init__(self, root, fileids, encoding)
	def _parse(self, s):
		d = self.d
		def getchildren(parent, children):
			results = []; head = None
			for n,a in children[parent]:
				# n is the index in the block to record word indices
				if a[WORD][0] == "#":
					results.append(Tree(a[TAG-d], getchildren(a[WORD][1:], children)))
				else:
					results.append(Tree(a[TAG-d], [n]))
				if head is None and "HD" in a[FUNC-d].split("-"): head = results[-1]
			# roughly order constituents by order in sentence
			results.sort(key=lambda a: a.leaves()[0])
			if head is None or not self.headorder: return results
			head = results.index(head)
			# everything until the head is reversed and prepended to the rest,
			# leaving the head as the first element
			if self.headfinal:
				if self.reverse:
					# head final, reverse rhs: A B C^ D E => A B E D C^
					return results[:head] + results[head:][::-1]
				else:
					# head final, no reverse:  A B C^ D E => D E A B C^
					#return sorted(results[head+1:] + results[:head]) + results[head:head+1]
					# head final, reverse lhs:  A B C^ D E => E D A B C^
					return results[head+1:][::-1] + results[:head+1]
			else:
				if self.reverse:
					# head first, reverse lhs: A B C^ D E => C^ B A D E
					return results[:head+1][::-1] + results[head+1:]
				else:
					# head first, reverse rhs: A B C^ D E => C^ D E B A
					return results[head:] + results[:head][::-1]
		children = {}
		for n,a in enumerate(s):
			children.setdefault(a[PARENT-d], []).append((n,a))
		return Tree("ROOT", getchildren("0", children))
	def _word(self, s):
		return [a[WORD] for a in s if a[WORD][0] != "#"]
	def _tag(self, s, ignore):
		return [(a[WORD], a[TAG-self.d]) for a in s if a[WORD][0] != "#"]
	def _read_block(self, stream):
		return [[line.split() for line in block.splitlines()[1:]] 
				for block in read_regexp_block(stream, BOS, EOS)]
			# didn't seem to help:
			#for b in map(lambda x: read_regexp_block(stream, BOS, EOS), range(1000)) for block in b]
	def blocks(self):
		def reader(stream):
			result = read_regexp_block(stream, BOS, EOS)
			return [re.sub(BOS,"", result[0])] if result else []
	        return concat([StreamBackedCorpusView(fileid, reader, encoding=enc)
        	               for fileid, enc in self.abspaths(self._fileids, True)])

tagtoconst = { 
	"NN" : "NP",
	"NE" : "NP",
	#"VVFIN" : "VP"		
	#"VAFIN" : "VP"		
}

def unfold(tree):
	# un-flatten PPs
	for pp in tree.subtrees(lambda n: n.node == "PP"):
		if (len(pp) == 2 and pp[1].node != "NP" or len(pp) > 2):
			np = Tree("NP", pp[1:])
			pp[:] = [pp[0], np]
	# introduce phrasal projections for single tokens
	for a in tree.treepositions("leaves"):
		tag = tree[a[:-1]]   # e.g. NN
		const = tree[a[:-2]] # e.g. S
		if tag.node in tagtoconst and const.node != tagtoconst[tag.node]:
			newconst = Tree(tagtoconst[tag.node], [tag])
			const[a[-2]] = newconst
	return tree

def fold(tree):
	# flatten PPs
	for pp in tree.subtrees(lambda n: n.node == "PP"):
		if len(pp) == 2 and pp[1].node == "NP":
			pp[:] = pp[:1] + pp[1][:]
	# remove phrasal projections for single tokens
	for a in tree.treepositions("leaves"):
		tag = tree[a[:-1]]   # NN
		const = tree[a[:-2]] # NP
		parent = tree[a[:-3]] # PP
		if len(const) == 1 and tag.node in tagtoconst and const.node == tagtoconst[tag.node]:
			parent[a[-3]] = tag
			del const
	return tree

def main():
	n = NegraCorpusReader(".", "sample2\.export")
	for a in n.parsed_sents(): print a
	for a in n.tagged_sents(): print a
	for a in n.sents(): print a
	for a in n.blocks(): print a
	nn = NegraCorpusReader(".", "sample2\.export", unfoldredundancy=True)
	for a,b in zip(n.parsed_sents(), nn.parsed_sents()):
		print b
		if a == fold(b): print "match"
		else: 
			print a
			print fold(b)
			print 

if __name__ == '__main__': main()
