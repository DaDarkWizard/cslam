import tree_sitter_c as tsc
import tree_sitter_matlab as tsm
import tree_sitter_python as tsp
import tree_sitter_java as tsj
from tree_sitter import Language, Parser
import tree_sitter
from pprint import pp
import sys
import os
import array
import json
import mysql.connector
import warnings
from map import Map
import zipfile
import io
import re

from livescriptparser import extract_livescript_code


with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    MATLAB_LANGUAGE = Language(tsm.language())
    C_LANGUAGE = Language(tsc.language())

PYTHON_LANGUAGE = Language(tsp.language())
JAVA_LANGUAGE = Language(tsj.language())
CURRENT_LANGUAGE = MATLAB_LANGUAGE


SQL_USER = "root"
SQL_PASSWORD = "h3llsp1r3$igns"

def contains(self, s):
    return (s.start_point[0] > self.start_point[0] or\
            (s.start_point[0] == self.start_point[0] and\
             s.start_point[1] >= self.start_point[1])) and\
           (s.end_point[0] < self.end_point[0] or\
            (s.end_point[0] == self.end_point[0] and\
             s.end_point[1] <= self.end_point[1]))

tree_sitter.Node.contains = contains

# -------------------------------------


# -------------------------------------

def default_match_result(pattern):
    critique = {}
    critique["start_line"] = 0
    critique["start_column"] = 0
    critique["start_position"] = 0
    critique["end_line"] = 0
    critique["end_column"] = 0
    critique["end_position"] = 0
    return critique


def match_pattern(tree, language, pattern, code, pattern_on_match=True):
    query = language.query(pattern)
    matches = query.matches(tree.root_node)

    critiques = []
    num_pass = 0

    add_no_match = False

    if len(matches) > 0:
        if code is not None:
            # Create an arg list
            args = code[code.index('(') + 1:code.index(')')]
            args = [s.strip() for s in args.split(',')]
            args = args[1:]

            exec(code)

        for match in matches:
            if "antipattern" not in match[1]:
                continue

            eval_result = True

            if code is not None:
                func_call = 'antipattern(tree, '
                for i, arg in enumerate(args):
                    func_call += "match[1]['" + args[i] + "']"
                    if i < len(args) - 1:
                        func_call += ', '
                func_call += ')'
                eval_result = eval(func_call, locals())

            if isinstance(eval_result, bool):
                if eval_result and pattern_on_match:
                    critique = default_match_result(match)
                    critique["start_line"] = match[1]['antipattern'][0].start_point[0] + 1
                    critique["start_column"] = match[1]['antipattern'][0].start_point[1] + 1
                    critique["end_line"] = match[1]['antipattern'][0].end_point[0] + 1
                    critique["end_column"] = match[1]['antipattern'][0].end_point[1] + 1
                    critiques.append(critique)
                elif not eval_result and not pattern_on_match:
                    add_no_match = True
                else:
                    num_pass += 1

            else:
                if (eval_result[0] and pattern_on_match):
                    critique = default_match_result(match)
                    critique["start_line"] = min(eval_result[1])
                    critique["start_column"] = 0
                    critique["end_line"] = max(eval_result[1])
                    critique["end_column"] = 0
                    critiques.append(critique)
                elif (not eval_result[0] and not pattern_on_match):
                    add_no_match = True
                else:
                    num_pass += 1

    elif len(matches) == 0 and not pattern_on_match:
        add_no_match = True

    if add_no_match:
        critique = default_match_result(match)
        critiques.append(critique)


    return (critiques, num_pass)

def test(pattern_conn, test_id):
    cur = pattern_conn.cursor()

    cur.execute(
        "SELECT text, result, pattern_id FROM pattern_test WHERE id=%s",
        (test_id,)
    )

    (test_text, correct_result, pattern_id) = cur.fetchone()

    # Assume new field code_string (nullable longtext)
    # update regex_string to longtext
    cur.execute(
        "SELECT regex_string, language, code_string FROM pattern WHERE id=%s",
        (pattern_id,)
    )

    (ast_search, language, code_match) = cur.fetchone()

    if language.lower() == "python":
        CURRENT_LANGUAGE = PYTHON_LANGUAGE
    elif language.lower() == "matlab":
        CURRENT_LANGUAGE = MATLAB_LANGUAGE
    elif language.lower() == "c":
        CURRENT_LANGUAGE = C_LANGUAGE
    elif language.lower() == "java":
        CURRENT_LANGUAGE = JAVA_LANGUAGE
    else:
        print("Unsupported language!")
        return -1


    parser = Parser(CURRENT_LANGUAGE)

    tree = parser.parse(bytes(test_text, "utf8"), encoding='utf8')
    matched = False

    res = match_pattern(tree, CURRENT_LANGUAGE, ast_search, code_match, True)

    if len(matches) > 0:
        matched = True

    passed = (matched and correct_result == 1) or (not matched and correct_result == 0)

    cur.execute(
        "UPDATE pattern_test SET pass=%s WHERE id=%s",
        (passed,test_id,)
    )
    pattern_conn.commit()

    if matched:
        print(1)
    else:
        print(0)

    return 0

def grade(pattern_conn, critique_id, f):

    global CURRENT_LANGUAGE

    # f = open("/tmp/testfile.txt", "a")
    # f.write("Critique id: " + str(critique_id))
    # Connect to the webta database

    try:
        assignment_conn = mysql.connector.connect(
            user=SQL_USER,
            password=SQL_PASSWORD,
            host="localhost",
            port=3306,
            database="engta",
            use_pure=True,
            raw=True
        )
    except mysql.connector.Error as e:
        print(f"Error connecting to MariaDB: {e}")
        return -1

    # Create the initial critique info
    main_critique = {}
    main_critique["version"] = 7
    main_critique["num_critical"] = 0
    main_critique["overall_status"] = ""
    main_critique["num_pass"] = 0
    main_critique["num_warning"] = 0
    main_critique["can_process_file"] = True
    main_critique["executive_summary"] = ""

    # Create our cursor
    assignment_cur = assignment_conn.cursor()

    max_wait = 1000

    assignment_cur.execute(
            "SELECT num_critical, num_pass, num_warning, submissionid from critique where id = %s",
            (critique_id,)
            )

    main_critique = assignment_cur.fetchone()

    while main_critique is None and max_wait > 0:
        assignment_cur.execute(
                "SELECT num_critical, num_pass, num_warning, submissionid from critique where id = %s",
                (critique_id,)
                )

        main_critique = assignment_cur.fetchone()
        max_wait -= 1;


    if main_critique is None:
        print("That critique does not exist")
        return -1

    num_critical=int(main_critique[0])
    num_pass=int(main_critique[1])
    num_warning = int(main_critique[2])

    submission_id = main_critique[3]

    # Make sure the assignment exists
    assignment_cur.execute(
        "SELECT id FROM submission WHERE id=%s",
        (submission_id,)
    )

    submission = assignment_cur.fetchone()

    if submission is None:
        print("That submission does not exist")
        return -1

    # Create the initial entry for the critique
    # assignment_cur.execute(
    #     "INSERT INTO critique (version, num_critical, date_created, overall_status, last_updated, num_pass, " +\
    #     "submission_id, num_warning, can_process_file, executive_summary) values (" +\
    #     "%s, 0, NOW(), '', NOW(), 0, %s, 0, 1, '');",
    #     (main_critique["version"],submission_id,)
    # )
    # assignment_conn.commit()

    # # Get the id of the entry
    # main_critique["id"] = assignment_conn.insert_id()

    # Get all files they submitted
    assignment_cur.execute(
        "SELECT id, version, file_data, filetype, " +\
        "filesize, filename FROM submission_file WHERE submissionid=%s",
        (submission_id,)
    )

    from mysql.connector import FieldType

    submitted_files = assignment_cur.fetchall()
    
    pattern_cur = pattern_conn.cursor()

    critiques = []

    for (file_id, file_version, file_data, file_type, file_size, file_name) in submitted_files:
        file_name = str(file_name, encoding="utf8")
        # Get the language we should use.
        if file_name.endswith(".py"):
            CURRENT_LANGUAGE = PYTHON_LANGUAGE
            language_name = "python"
            file_data = file_data.decode('utf-8')
        elif file_name.endswith(".m"):
            CURRENT_LANGUAGE = MATLAB_LANGUAGE
            language_name = "matlab"
            file_data = str(file_data, encoding='utf-8')
        elif file_name.endswith(".mlx"):
            CURRENT_LANGUAGE = MATLAB_LANGUAGE
            language_name = "matlab"
            import traceback
            try:
                file_data = extract_livescript_code( file_data )
            except:
                print(traceback.format_exc(), file=sys.stderr)
        elif file_name.endswith(".c"):
            CURRENT_LANGUAGE = C_LANGUAGE
            language_name = "c"
            file_data = file_data.decode('utf-8')
        elif file_name.endswith(".java"):
            CURRENT_LANGUAGE = JAVA_LANGUAGE
            language_name = "java"
            file_data = file_data.decode('utf-8')
        else:
            continue

        parser = Parser(CURRENT_LANGUAGE)
        tree = parser.parse(bytes(file_data, "utf8"), encoding='utf8')

        pattern_cur.execute(
            "SELECT id, title, regex_string, code_string, text, short_text, kind, on_match, citation," +\
            "severity, description from pattern where LOWER(language)=%s and engine=%s and is_disabled!=1",
            (language_name,"treesitter",)
        )

        # for (pattern_id, pattern_name, query_string, code_string, pattern_text, pattern_short_text, pattern_kind,\
        #         pattern_on_match, pattern_citation, pattern_severity, pattern_description) in pattern_cur:
        for pattern_tuple in pattern_cur:
            pattern = Map()
            pattern.id = pattern_tuple[0]
            pattern.pattern_id = pattern_tuple[0]
            pattern.title = pattern_tuple[1]
            pattern.regex_string = pattern_tuple[2]
            pattern.query_string = pattern.regex_string
            pattern.code_string = pattern_tuple[3]
            pattern.text = pattern_tuple[4]
            pattern.short_text = pattern_tuple[5]
            pattern.kind = pattern_tuple[6]
            pattern.on_match = pattern_tuple[7]
            pattern.pattern_on_match = pattern_tuple[7]
            pattern.citation = pattern_tuple[8]
            pattern.severity = pattern_tuple[9]
            pattern.description = pattern_tuple[10]
            query = CURRENT_LANGUAGE.query(pattern["regex_string"])
            matches = query.matches(tree.root_node)

            # Make sure code is real
            if pattern.code_string is not None and pattern.code_string.strip() == "":
                pattern.code_string = None

            (pattern_critiques, pattern_passing) = match_pattern(tree, CURRENT_LANGUAGE, pattern.query_string, pattern.code_string, bool(pattern.pattern_on_match))

            print(pattern.title, file=sys.stderr)
            print(pattern_critiques, file=sys.stderr)
            print(pattern_passing, file=sys.stderr)

            num_pass += pattern_passing
            
            for critique in pattern_critiques:
                critique["issue_kind"] = pattern.severity
                critique["issue_source"] = ''
                critique["critique_item_type"] = "PARSE_TIME"
                critique["text"] = pattern.text
                critique["patternid"] = pattern.id
                critique["is_native_method"] = 0
                critique["submission_file_id"] = file_id
                critique["severity"] = pattern.severity
                critique["name"] = pattern.title
                critique["priority"] = 0
                if pattern.severity.lower() in ["error", "fail", "critical"]:
                    critique["status"] = "CRITICAL"
                elif pattern.severity.lower() in ["warning", "comment"]:
                    critique["status"] = "WARNING"
                elif pattern.severity.lower() in ["pass"]:
                    critique["status"] = "OK"
                else:
                    critique["status"] = "UNKNOWN"
                critique["alt_text"] = pattern.short_text
                critique["issue_type"] = 'PATTERN_ISSUE'
                critique["description"] = pattern.description
                critiques.append(critique)

    for critique in critiques:

        if critique["status"] == "CRITICAL":
            num_critical += 1
        elif critique["status"] == "WARNING":
            num_warning += 1

        print(critique["name"], file=sys.stderr)

        assignment_cur.execute(
            "INSERT INTO critique_item(version, start_column, start_position, " +\
            "column_num, date_created, issue_kind, line, last_updated, issue_source, " +\
            "critique_item_type, text, patternid, is_native_method, submission_file_id, " +\
            "start_line, severity, position, name, priority, critique_id, end_line, status, " +\
            "end_position, alt_text, issue_type, description, end_column) " +\
            "values(%s, %s, %s, %s, NOW(), %s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (7, critique["start_column"], critique["start_position"], critique["start_column"], critique["issue_kind"],\
            critique["start_line"], critique["issue_source"], critique["critique_item_type"], critique["text"],\
            critique["patternid"], critique["is_native_method"], critique["submission_file_id"], critique["start_line"],\
            critique["severity"], critique["start_position"], critique["name"], critique["priority"], critique_id,\
            critique["end_line"], critique["status"], critique["end_position"], critique["alt_text"], critique["issue_type"],\
            critique["description"], critique["end_column"],)
        )

        assignment_conn.commit()

    assignment_cur.execute(
        "UPDATE critique SET num_pass=%s, num_critical=%s, num_warning=%s where id=%s",
        (num_pass, num_critical, num_warning, critique_id,)
    )

    assignment_conn.commit()

    print(len(critiques))
    return 0        


def check_submissions(classid, engta):

    engta_cur = engta.cursor()

    submissions = []

    engta_cur.execute("SELECT id from submission where courseid=%s", (classid,))

    for submission in engta_cur:
        submissions.append(submission[0])

    filetypes = set()

    no_header_matches = 0
    bad_header_matches = 0

    parser = Parser(MATLAB_LANGUAGE)

    query_string_no_header = "(source_file . (comment)+  ) @antipattern"
    code_string_no_header = None

    for submission in submissions:
        contains_header = True
        engta_cur.execute("SELECT id, file_data, filename from submission_file where submissionid=%s", (submission,))

        for (file_id, file_data, file_name) in engta_cur:
            # Get the language we should use.
            if file_name.endswith(".m"):
                language_name = "matlab"
                file_data = str(file_data, encoding='utf-8')
            elif file_name.endswith(".mlx"):
                CURRENT_LANGUAGE = MATLAB_LANGUAGE
                language_name = "matlab"
                import traceback
                try:
                    print(type(file_data))
                    file_data = extract_livescript_code( file_data)
                    print("Good zip")
                except:
                    #print("failed zip")
                    print(traceback.format_exc(), file=sys.stderr)
            else:
                continue

            tree = parser.parse(bytes(file_data, "utf8"), encoding='utf8')
            (pattern_critiques, pattern_passing) = match_pattern(tree, MATLAB_LANGUAGE, query_string_no_header, code_string_no_header, pattern_on_match=True)
            if len(pattern_critiques) > 0:
                contains_header = True

    print("Class id: " + str(classid))
    print("No header matches: " + str(no_header_matches))
    print("Bad header matches: " + str(bad_header_matches))



def main():
    if len(sys.argv) > 1:
        print("This CSLAM has been modified for the 2026 SIGCSE submission.")
        return -1

    
    #parser = Parser(CURRENT_LANGUAGE)


    try:
        pattern_conn = mysql.connector.connect(
            user=SQL_USER,
            password=SQL_PASSWORD,
            host="192.168.1.109",
            port=3306,
            database="engta",
            use_pure=True
        )
    except mysql.connector.Error as e:
        print(f"Error connecting to MariaDB: {e}")
        return -1

    check_submissions(5, pattern_conn)


if __name__ == '__main__':
    main()

