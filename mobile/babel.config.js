module.exports = function (api) {
  api.cache(true);
  return {
    presets: [["babel-preset-expo", { jsxImportSource: "nativewind" }]],
    plugins: [
      // Replace import.meta.env with process.env (Zustand + other libs use it in dev)
      function importMetaEnvPlugin() {
        return {
          visitor: {
            MetaProperty(path) {
              // import.meta.env.X -> process.env.X
              const { parent } = path;
              if (
                parent.type === "MemberExpression" &&
                parent.property.type === "Identifier" &&
                parent.property.name === "env"
              ) {
                path.replaceWithSourceString("process");
              }
              // bare import.meta -> { env: process.env }
              else if (
                parent.type !== "MemberExpression" ||
                parent.property.name !== "env"
              ) {
                path.replaceWithSourceString("({ env: process.env })");
              }
            },
          },
        };
      },
      "react-native-reanimated/plugin",
    ],
  };
};
