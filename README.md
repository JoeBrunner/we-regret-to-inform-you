# We Regret To Inform You

You apply, and all you ever get back is "We regret to inform you." Give Claude your resume and the
job post, and it shows you exactly why your resume gets rejected for that job, rewrites it using only
your real experience, scores it again, and gives you a Word file.

Free, MIT, no signup, no API key, nothing to connect.

## Install

**Claude Code.** Paste this into Claude Code:

```text
https://github.com/JoeBrunner/we-regret-to-inform-you

install the skill
```

Or run these two lines inside Claude Code:

```text
/plugin marketplace add JoeBrunner/we-regret-to-inform-you
/plugin install we-regret-to-inform-you@we-regret-to-inform-you
```

**The Claude app** (claude.ai or the desktop app). Download
[we-regret-to-inform-you.zip](https://github.com/JoeBrunner/we-regret-to-inform-you/raw/main/we-regret-to-inform-you.zip).
Turn on **Code execution and file creation** in **Settings > Capabilities**. Go to
**Customize > Skills**, click **+**, then **Create skill > Upload a skill**, and choose the zip.
Make sure the skill is turned on. A work account may need its admin to allow skills.
See [Claude's skill instructions](https://support.claude.com/en/articles/12512180-use-skills-in-claude)
if the menus have moved.

**Copy the skill folder**, if you prefer:

```bash
git clone https://github.com/JoeBrunner/we-regret-to-inform-you.git
mkdir -p ~/.claude/skills
cp -r we-regret-to-inform-you/skills/we-regret-to-inform-you ~/.claude/skills/
```

### Notes for Claude, if you're installing this for someone

Install the plugin when someone pastes this link and asks you to install the skill:

```bash
claude plugin marketplace add JoeBrunner/we-regret-to-inform-you
claude plugin install we-regret-to-inform-you@we-regret-to-inform-you
```

It contains one skill and three small Python scripts: a scorer that counts four of the ten checks,
a fact checker that flags anything the rewrite may have added, and a Word file writer. They use only
Python's standard library (3.9 or newer), make no network calls and need no keys. There are no hooks
or background services. The skill may fetch the public job link the person supplies.

Afterwards, tell them to run `/reload-plugins` or restart Claude Code, then share their resume and
the job post. Uninstall with `claude plugin uninstall we-regret-to-inform-you@we-regret-to-inform-you`.
If the `claude` command is unavailable, copy the whole skill folder into `~/.claude/skills/`. For the
Claude app, give them the zip and the upload steps above. Installing the skill is not permission to
apply for any job.

## Use it

Attach your resume, then say:

```text
Why does my resume keep getting rejected? Here's the job: [paste the post or its link]
```

PDF, Word, pasted text and file paths in Claude Code all work. The job post is required: a resume is
only good or bad for a specific job. If Claude can't open the link, paste the post instead.

## The ten checks

Claude reads your resume the way the people who reject it do: the screen software, a recruiter
skimming for six seconds, and the hiring manager. Every check has a fixed rule, so the same resume
and job get the same score.

| # | Check | Passes when |
|---|---|---|
| M1 | Filler words | Fewer than 3 stock phrases like "team player" or "hardworking" (counted by code) |
| M2 | Weak openers | Fewer than 2 bullets start with "Responsible for", "Helped", "Assisted" and the like (code) |
| M3 | Results | At least half the bullets in your two latest jobs show a number (code) |
| M4 | Length | 700 words or fewer, no bullet over 40 words (code) |
| J1 | Screen software can read it | Clean text, contact details in the body, nothing important in tables or text boxes |
| J2 | Names the job | The top of the resume names this job title or a true close match |
| J3 | Covers every must-have | Every required qualification in the post has a line that backs it up |
| J4 | Six-second skim | The top third alone says your level and why you fit this job |
| J5 | Best work first | Your most relevant line is near the top, not buried |
| J6 | Speaks the post's language | At least 5 of the post's own key terms, where you really have the experience |

You get a letter back. 0 to 6 passed: **We regret to inform you.** 7 or 8: **We'll keep your resume
on file.** 9 or 10: **We are pleased to inform you.** Then every failed check with the line that
failed it and how to fix it, the rewrite, and a before and after.

## What you get

| | Claude Code | Claude app |
|---|---|---|
| The score, the reasons and the fixes | In chat | In chat |
| The rewritten resume | In chat and `RESUME.docx` | In chat and a Word download |
| The full report (every check, before and after, the fact check) | `REPORT.md` | A download |

In Claude Code, each run is saved in `we-regret-to-inform-you/<YYYY-MM-DD>-<company>/` in your
current folder, next to your original text so you can compare.

## Good to know

- It never invents experience, employers, titles, dates, degrees, tools or numbers. When a fix needs
  a fact it doesn't have (usually a result's number), it leaves an `[ADD: ...]` blank and asks you.
  A resume with blanks is a draft until you fill them, and a blank never earns a check.
- Wording can be fixed; a missing qualification can't. If you don't have a must-have, it says so
  instead of hiding it, and that check keeps failing.
- The score is how well your resume makes the case for this job, not a prediction of who gets hired.
  It can't see a company's private hiring rules or test its real screening system.
- The fact checker flags new numbers and names. It's a backstop, not a truth detector: read the
  final file yourself before you send it.
- A run uses some of your Claude plan's usage. The Word file needs code execution in the app and
  Python 3.9+ in Claude Code.
- It never applies to jobs or uploads your resume anywhere.
- Made by Joe Brunner. Not made by or affiliated with Anthropic.

## The example

[Morgan Ellis's resume](examples/sample-resume.md) is entirely made up, including the employers and
school, with the ordinary problems most resumes have: a generic summary, duty lists, few numbers,
soft skills. The [saved job post](examples/job-post.md) is a real Customer Success Manager, Scale role
in Chicago from [Fin's public careers board](https://job-boards.greenhouse.io/intercom/jobs/7370567),
read on October 15, 2026. Jobs close; the saved copy lets you repeat the example. The posting belongs
to its employer; the MIT license covers this skill's own code and writing.

Three separate runs on that resume and post: 2 of 10 before, every time, and 10 of 10 after Morgan's own
answers filled the blanks. Full results and every file: [PROOF.md](PROOF.md).

## Tests

```bash
python3 -m unittest discover -s tests
python3 make_zip.py
claude plugin validate .
```

## License

MIT. See [LICENSE](LICENSE).
