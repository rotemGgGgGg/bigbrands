// RTM WATCHES — central product catalogue.
// Prices are illustrative display prices for the mockup, not live market quotes.
// Image paths are configurable: replace a file in assets/watches/ (keep ~1:1 ratio) or point `image` elsewhere.
window.RTM_PRODUCTS = [
  { id: 'rolex-gmt-master-ii', brand: 'Rolex', model: 'GMT-Master II', price: 17900, currency: 'USD',
    image: 'assets/watches/rolex-gmt-master-ii.jpg', collections: ['new-arrivals', 'best-sellers', 'summer'],
    accent: 'blue', description: 'Steel GMT with two-tone black and blue bezel.' },
  { id: 'rolex-daytona', brand: 'Rolex', model: 'Daytona', price: 29800, currency: 'USD',
    image: 'assets/watches/rolex-daytona.jpg', collections: ['best-sellers', 'winter', 'limited'],
    accent: 'gold', description: 'Steel chronograph with white dial and black subdials.' },
  { id: 'patek-nautilus-5711', brand: 'Patek Philippe', model: 'Nautilus 5711', price: 92000, currency: 'USD',
    image: 'assets/watches/patek-nautilus-5711.jpg', collections: ['best-sellers', 'summer', 'limited'],
    accent: 'gold', description: 'Integrated-bracelet steel sports watch, blue dial.' },
  { id: 'ap-royal-oak-15510', brand: 'Audemars Piguet', model: 'Royal Oak 15510', price: 41900, currency: 'USD',
    image: 'assets/watches/ap-royal-oak-15510.jpg', collections: ['new-arrivals', 'winter'],
    accent: 'silver', description: 'Octagonal bezel, Grande Tapisserie blue dial.' },
  { id: 'richard-mille-rm011', brand: 'Richard Mille', model: 'RM 011', price: 310000, currency: 'USD',
    image: 'assets/watches/richard-mille-rm011.jpg', collections: ['limited', 'winter'],
    accent: 'red', description: 'Tonneau-cased flyback chronograph in black with red accents.' },
  { id: 'rolex-datejust-41', brand: 'Rolex', model: 'Datejust 41', price: 13900, currency: 'USD',
    image: 'assets/watches/rolex-datejust-41.jpg', collections: ['new-arrivals', 'summer'],
    accent: 'gold', description: 'Fluted bezel, green dial, Jubilee bracelet.' },
  { id: 'cartier-santos', brand: 'Cartier', model: 'Santos', price: 7900, currency: 'USD',
    image: 'assets/watches/cartier-santos.jpg', collections: ['new-arrivals', 'summer'],
    accent: 'silver', description: 'Square steel case with Roman-numeral dial.' },
  { id: 'rolex-day-date-40', brand: 'Rolex', model: 'Day-Date 40', price: 38500, currency: 'USD',
    image: 'assets/watches/rolex-day-date-40.jpg', collections: ['best-sellers', 'limited', 'summer'],
    accent: 'gold', description: 'Yellow-gold case and President bracelet.' },
  { id: 'omega-speedmaster', brand: 'Omega', model: 'Speedmaster', price: 6900, currency: 'USD',
    image: 'assets/watches/omega-speedmaster.jpg', collections: ['best-sellers', 'winter'],
    accent: 'silver', description: 'Black-dial steel chronograph.' },
  { id: 'rolex-submariner', brand: 'Rolex', model: 'Submariner', price: 16900, currency: 'USD',
    image: 'assets/watches/rolex-submariner.jpg', collections: ['new-arrivals', 'winter'],
    accent: 'silver', description: 'Black dial and ceramic bezel dive watch.' }
];

window.RTM_COLLECTIONS = [
  { id: 'new-arrivals', label: 'New Arrivals' },
  { id: 'best-sellers', label: 'Best Sellers' },
  { id: 'summer', label: 'Summer Collection' },
  { id: 'winter', label: 'Winter Collection' },
  { id: 'limited', label: 'Limited Edition' }
];
