# Security Policy

`rust-safety` is documentation and guidance, but incorrect safety guidance can be security-relevant when it is systematically applied to generated or reviewed Rust code. Soundness defects in this Skill are therefore in scope when they can plausibly create memory-safety, confidentiality, integrity, or availability risk.

## Supported versions

| Version | Security fixes |
|---|---|
| Default branch | Supported |
| Latest `0.1.x` release | Supported |
| Older release lines | Not supported unless explicitly announced |

Security fixes are normally made on the default branch first. Backports are handled only for the supported release line when a released version exists.

## What to report privately

Use a private disclosure channel for reports that contain or depend on any of the following:

- an undisclosed exploit or practical attack path;
- a soundness flaw that could lead to memory unsafety or unsafe API misuse;
- concrete steps for triggering externally reachable denial of service or resource exhaustion;
- secret, credential, private data, or non-public infrastructure details;
- another security-sensitive issue where public disclosure before a fix would materially increase risk.

Ordinary documentation errors that do not expose non-public exploit details can use the normal bug or safety-correction templates.

## Private reporting channels

Choose the private mechanism provided by the repository host.

### GitHub

Use **Security and quality → Report a vulnerability** / GitHub Private Vulnerability Reporting when it is enabled for the repository. Do not open a public GitHub issue containing undisclosed exploit details or secrets.

GitHub documentation: <https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/report-privately>

### GitLab

Create a GitLab issue and mark it **Confidential** before submitting security-sensitive details. Verify that the issue is shown as confidential before adding exploit information or secrets.

GitLab documentation: <https://docs.gitlab.com/user/project/issues/confidential_issues/>

### If no private channel is available

Do **not** publish the sensitive details. Open only a minimal public issue stating that you need a private security contact channel, without exploit steps, secrets, affected private systems, or other disclosure-sensitive information. A maintainer can then establish an appropriate private channel.

## What to include

When possible, include:

- the affected rule, reference, example, or validator behavior;
- affected versions or commit range;
- the security or soundness property that is violated;
- a minimal reproduction or proof, shared privately when sensitive;
- expected safe behavior;
- a narrowly scoped correction, if known.

Do not include real credentials or personal data. Use synthetic values in reproductions whenever possible.

## Handling and disclosure

Maintainers should limit report access to people needed to investigate and fix the issue. Public disclosure should avoid unnecessary exploit detail until a correction is available or coordinated disclosure is otherwise appropriate.

This project does not promise a fixed response or remediation SLA. Reports are prioritized according to demonstrated impact, exploitability, affected versions, and maintainer capacity.
