const pastelColors = [
  "bg-rose-400",
  "bg-lime-400",
  "bg-cyan-400",
  "bg-purple-400",
  "bg-pink-400",
  "bg-orange-400",
  "bg-teal-400",
];

const FeatureCard = ({ title, subtitle, bgColor }) => (
  <div
    className={`rounded-2xl p-10 shadow-md text-black flex flex-col justify-between ${bgColor}`}
  >
    <div>
      <h2 className="text-xl font-mono leading-tight">{title}</h2>
      <p className="text-sm mt-2 font-mono opacity-100 font-light">
        {subtitle}
      </p>
    </div>
  </div>
);

const Cards = ({ features }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 gap-4 p-6 w-full max-w-screen-xl mx-auto">
      {features.map((item, index) => (
        <FeatureCard
          key={index}
          title={item.title}
          subtitle={item.subtitle}
          bgColor={pastelColors[index % pastelColors.length]}
        />
      ))}
    </div>
  );
};

export default Cards;
