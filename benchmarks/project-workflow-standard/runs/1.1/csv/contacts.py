import argparse
import csv
import json


def read_contacts(path):
    contacts = []
    seen_emails = set()
    with open(path, encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        # Пустые строки до заголовка тоже не являются контактами.
        while fieldnames is not None and not any(name.strip() for name in fieldnames):
            reader.fieldnames = None
            fieldnames = reader.fieldnames
        if fieldnames is None:
            return contacts
        reader.fieldnames = [name.strip() for name in fieldnames]

        for row in reader:
            contact = {
                name: value.strip() if isinstance(value, str) else value
                for name, value in row.items()
            }
            if not any(contact.values()):
                continue
            email = contact.get("email") or ""
            if not email:
                raise ValueError(f"Строка {reader.line_num}: Email не может быть пустым.")
            normalized_email = email.casefold()
            if normalized_email in seen_emails:
                raise ValueError(
                    f"Строка {reader.line_num}: Повтор email: {normalized_email}."
                )
            seen_emails.add(normalized_email)
            contacts.append(contact)
    return contacts


def _non_negative_int(value):
    message = "--limit должен быть целым неотрицательным числом"
    try:
        limit = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(message) from error
    if limit < 0:
        raise argparse.ArgumentTypeError(message)
    return limit


def main():
    parser = argparse.ArgumentParser(description="Импорт контактов из CSV в JSON")
    parser.add_argument("path")
    parser.add_argument(
        "--limit", type=_non_negative_int, metavar="N",
        help="вывести первые N контактов (по умолчанию все)",
    )
    args = parser.parse_args()
    try:
        contacts = read_contacts(args.path)
    except ValueError as error:
        parser.error(str(error))
    if args.limit is not None:
        contacts = contacts[:args.limit]
    print(json.dumps(contacts, ensure_ascii=False))


if __name__ == "__main__":
    main()
