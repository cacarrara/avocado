import argparse
import re
from subprocess import CalledProcessError, check_output


class AvocadoLintReport:
    def __init__(self, directories='avocado,optional_plugins', consolidate=True, verbose=False):
        self.pylint_msgs = self._pylint_msgs_dict()
        self.verbose = verbose
        self.consolidate = consolidate
        self.directories = directories.split(',')
        self.lint_codes = {}

        for _dir in self.directories:
            pylint_output = self._pylint_output(_dir)
            setattr(self, '%s_lint_codes' % _dir, self._get_codes_from(pylint_output))
            self.lint_codes[_dir] = getattr(self, '%s_lint_codes' % _dir)

    def _pylint_output(self, directory):
        try:
            return check_output(['pylint', directory]).decode('UTF-8')
        except CalledProcessError as e:
            return e.output.decode('UTF-8')

    def _get_codes_from(self, pylint_output):
        codes = []
        for line in pylint_output.splitlines():
            search_result = re.search(r'[A-Z]{1}\d{4}', line)
            if not search_result:
                continue
            code = search_result.group(0)
            codes.append(code)
        codes = list(set(codes))
        codes.sort()
        return codes

    def _pylint_msgs_dict(self):
        raw_msgs = check_output(['pylint', '--list-msgs']).decode('UTF-8')
        msgs_dict = dict()
        last_code = None
        for line in raw_msgs.splitlines():
            if line.startswith(':'):
                end_of_name = line.find(' ')
                end_of_code = line.find(')')
                start_desc = line.find('*')
                msg_name = line[1:end_of_name]
                msg_code = line[end_of_name + 2:end_of_code]
                msg_desc = line[start_desc + 1:-1]
                msg_dict = {
                    'name': msg_name,
                    'description': msg_desc,
                    'details': '',
                }
                msgs_dict[msg_code] = msg_dict
                last_code = msg_code
            else:
                msgs_dict[last_code]['details'] += line.strip()
        return msgs_dict

    def _get_details_from(self, codes):
        result = {}
        for code in codes:
            result[code] = self.pylint_msgs[code]
        return result

    def _build_output(self, lint_codes):
        output = ''
        if not self.verbose:
            output += '%s\n' % ','.join(lint_codes)
        else:
            for code in lint_codes:
                output += '{} - {} ({})\n'.format(
                    code,
                    self.pylint_msgs[code]['name'],
                    self.pylint_msgs[code]['description'],
                )
        return output

    def lint_errors(self):
        output = ''
        if not self.consolidate:
            for _dir in self.directories:
                lint_codes = self.lint_codes[_dir]
                output += '%s\n%s\n' % (_dir, self._build_output(lint_codes))
        else:
            lint_codes = []
            for _dir in self.directories:
                lint_codes.extend(self.lint_codes[_dir])
            lint_codes = sorted(list(set(lint_codes)))
            output += self._build_output(lint_codes)

        return output
        
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', help='activate verbose mode', action='store_true')
    parser.add_argument('--directories',
                        help='inform directories (separated by commas) to run script on',
                        default='avocado,optional_plugins')
    parser.add_argument('--consolidate',
                        help='activate verbose mode',
                        action='store_true')
    args = parser.parse_args()

    report = AvocadoLintReport(
        directories=args.directories,
        consolidate=args.consolidate,
        verbose=args.verbose
    )

    print(report.lint_errors())
