export default function Footer() {
  return (
    <footer className="border-t border-border-primary bg-surface">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
          <div>
            <h3 className="font-semibold text-text-primary">Product</h3>
            <ul className="mt-4 space-y-2">
              <li>
                <a
                  href="#"
                  className="text-sm text-text-secondary hover:text-mochi-primary"
                >
                  Features
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-sm text-text-secondary hover:text-mochi-primary"
                >
                  Pricing
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-sm text-text-secondary hover:text-mochi-primary"
                >
                  Security
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="font-semibold text-text-primary">Developers</h3>
            <ul className="mt-4 space-y-2">
              <li>
                <a
                  href="#"
                  className="text-sm text-text-secondary hover:text-mochi-primary"
                >
                  Documentation
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-sm text-text-secondary hover:text-mochi-primary"
                >
                  API Reference
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-sm text-text-secondary hover:text-mochi-primary"
                >
                  GitHub
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="font-semibold text-text-primary">Company</h3>
            <ul className="mt-4 space-y-2">
              <li>
                <a
                  href="#"
                  className="text-sm text-text-secondary hover:text-mochi-primary"
                >
                  About
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-sm text-text-secondary hover:text-mchio-primary"
                >
                  Blog
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-sm text-text-secondary hover:text-mchio-primary"
                >
                  Contact
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="font-semibold text-text-primary">Legal</h3>
            <ul className="mt-4 space-y-2">
              <li>
                <a
                  href="#"
                  className="text-sm text-text-secondary hover:text-mchio-primary"
                >
                  Privacy
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-sm text-text-secondary hover:text-mchio-primary"
                >
                  Terms
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 border-t border-border-primary pt-8">
          <p className="text-center text-sm text-text-secondary">
            © 2024 Weather Parametric Insurance. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}