import tree_sitter_c as tsc
from tree_sitter import Language, Parser
import tree_sitter
from pprint import pp
import sys
import os
import array
import json

C_LANGUAGE = Language(tsc.language())
CURRENT_LANGUAGE = C_LANGUAGE
EXPRESSIONS_FOLDER = "C:/Users/Madly/source/repos/cslam/expressions/"


# tree_sitter.Node.within = property(lambda self, s:
#                             s.start_point[0] >= self.start_point[0] and\
#                                     s.start_point[0] >= self.start_point[1] and\
#                                     s.end_point[0] <= self.end_point[0] and\
#                                     s.end_point[1] <= self.end_point[1]
#                         )

def contains(self, s):
    return (s.start_point[0] > self.start_point[0] or\
            (s.start_point[0] == self.start_point[0] and\
             s.start_point[1] >= self.start_point[1])) and\
           (s.end_point[0] < self.end_point[0] or\
            (s.end_point[0] == self.end_point[0] and\
             s.end_point[1] <= self.end_point[1]))

tree_sitter.Node.contains = contains


def main():
    if len(sys.argv) != 3:
        print("Usage: python astmatch.py <expressions_folder> <input_file>")
        return

    EXPRESSIONS_FOLDER = sys.argv[1]

    parser = Parser(CURRENT_LANGUAGE)

    with open(sys.argv[2], 'rb') as code_file:
        results = []
        tree = parser.parse(code_file.read(), encoding='utf8')

        for file_name in os.listdir(EXPRESSIONS_FOLDER):
            if ("test" in file_name):
                continue
            with open(EXPRESSIONS_FOLDER + file_name, 'r') as query_file:
                query_text = query_file.read()
                query_code = None
                query_comment = None

                if "ANTIPATTERN COMMENT" in query_text:
                    query_comment = query_text[query_text.index("ANTIPATTERN COMMENT") + 20:-1]
                    query_text = query_text[0:query_text.index("ANTIPATTERN COMMENT") - 1]

                if "def antipattern(" in query_text:
                    query_code = query_text[query_text.index("def antipattern("):-1]
                    query_text = query_text[0:query_text.index("def antipattern(") - 1]

                query = CURRENT_LANGUAGE.query(query_text)
                matches = query.matches(tree.root_node)

                if len(matches) > 0:
                    if query_code is not None:
                        # Create an arg list
                        args = query_code[query_code.index('(') + 1:query_code.index(')')]
                        args = [s.strip() for s in args.split(',')]
                        args = args[1:]

                        exec(query_code)

                        for match in matches:
                            func_call = 'antipattern(tree, '
                            
                            for i, arg in enumerate(args):
                                func_call += "match[1]['" + args[i] + "']"
                                if i < len(args) - 1:
                                    func_call += ', '
                            func_call += ')'
                            eval_result = eval(func_call)
                            result = {}
                            if isinstance(eval_result, bool):
                                if eval_result:
                                    result["name"] = file_name[0:-4]
                                    if query_comment is not None:
                                        result["comment"] = query_comment
                                    result["lines"] = [
                                        match[1]['antipattern'][0].start_point[0] + 1
                                    ]
                                    results.append(result)
                            else:
                                if eval_result[0]:
                                    result["name"] = file_name[0:-4]
                                    if query_comment is not None:
                                        result["comment"] = query_comment
                                    result["lines"] = eval_result[1]
                                    results.append(result)

                    else:
                        for match in matches:
                            result = {}
                            result["name"] = file_name[0:-4]
                            if query_comment is not None:
                                result["comment"] = query_comment
                            result["lines"] = [match[1]['antipattern'][0].start_point[0] + 1]
                            results.append(result)
        print(json.dumps(results))

if __name__ == '__main__':
    main()
