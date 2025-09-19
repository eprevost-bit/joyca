const accessKey = 'QAc9BMeDeHSOo1pURQNKGDmma9uVL4IcOB4Jz3ApAzM';
const placeholderImage = '/deskent_unsplash_images/static/description/image.png';
const fallbackImage = '/deskent_unsplash_images/static/description/image.png';

const getRandomPhotos = async () => {
  console.log("Loading API...");
  document.body.style.backgroundImage = `url(${placeholderImage})`;
  document.body.style.backgroundSize = 'cover';
  document.body.style.backgroundRepeat = 'no-repeat';

  const storedImageUrl = localStorage.getItem("backgroundImageUrl");
  if (storedImageUrl) {
    document.body.style.backgroundImage = `url(${storedImageUrl})`;
    return;
  }

  const url = `https://api.unsplash.com/photos/random?client_id=${accessKey}&count=1`;
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error('Failed to fetch random photos');
    }
    const data = await response.json();
    console.log("Images fetched successfully:", data);
    const imageUrl = data[0].urls.regular;
    localStorage.setItem("backgroundImageUrl", imageUrl);
    const img = new Image();
    img.src = imageUrl;
    img.onload = () => {
      document.body.style.backgroundImage = `url(${imageUrl})`;
    };
  } catch (error) {
    console.error('Error fetching data from Unsplash:', error);
    document.body.style.backgroundImage = `url(${fallbackImage})`;
  }
};

if (window.location.pathname === '/web/login') {
  getRandomPhotos();
}
