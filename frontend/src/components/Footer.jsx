export default function Footer() {
  return (
    <footer className="border-t border-navy-100 bg-white">
      <div className="mx-auto max-w-6xl px-4 py-5 sm:px-6">
        <p className="text-center text-[11px] leading-relaxed text-navy-300">
          This is an informational assistant for the Department of Justice, Ministry of Law
          &amp; Justice, Government of India. It does not constitute legal advice and does not
          replace official portals. For case status, use{" "}
          <a href="https://ecourts.gov.in" target="_blank" rel="noreferrer" className="text-navy-500 underline underline-offset-2">
            eCourts
          </a>{" "}
          or the{" "}
          <a href="https://njdg.ecourts.gov.in" target="_blank" rel="noreferrer" className="text-navy-500 underline underline-offset-2">
            National Judicial Data Grid
          </a>
          . For official information, visit{" "}
          <a href="https://doj.gov.in" target="_blank" rel="noreferrer" className="text-navy-500 underline underline-offset-2">
            doj.gov.in
          </a>
          .
        </p>
      </div>
    </footer>
  );
}
