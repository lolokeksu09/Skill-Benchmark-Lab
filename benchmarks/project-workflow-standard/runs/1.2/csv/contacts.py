import argparse
import csv
import json


def read_contacts(path):
    contacts = []
    seen_emails = set()
    fieldnames = None
    with open(path, encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        for values in reader:
            values = [value.strip() for value in values]
            if not any(values):
                continue
            if fieldnames is None:
                fieldnames = values
                continue
            if len(values) > len(fieldnames):
                raise ValueError(f"Too many columns on CSV line {reader.line_num}")
            contact = {
                name: values[index] if index < len(values) else ""
                for index, name in enumerate(fieldnames)
            }
            email = contact.get("email", "")
            if not email:
                raise ValueError(f"Missing email on CSV line {reader.line_num}")
            email_key = email.casefold()
            if email_key in seen_emails:
                raise ValueError(
                    f"Duplicate email {email!r} on CSV line {reader.line_num}"
                )
            seen_emails.add(email_key)
            contacts.append(contact)
    return contacts


def nonnegative_int(value):
    try:
        limit = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a non-negative integer") from None
    if limit < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return limit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument(
        "--limit", type=nonnegative_int,
        help="maximum number of contacts to output (default: all)",
    )
    args = parser.parse_args()
    try:
        contacts = read_contacts(args.path)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(contacts[:args.limit], ensure_ascii=False))


if __name__ == "__main__":
    main()
