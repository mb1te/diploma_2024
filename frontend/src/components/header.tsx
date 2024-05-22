import Icon from "./icons";
import { Disclosure, Menu, Transition } from "@headlessui/react";
import {
  XMarkIcon,
  Bars3Icon,
  BellIcon,
  MoonIcon,
  SunIcon,
} from "@heroicons/react/24/outline";
import { Fragment } from "react";
import { appContext } from "../hooks/provider";
import { Link } from "gatsby";
import React from "react";

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(" ");
}

const Header = ({ meta, link }: any) => {
  const { user, logout } = React.useContext(appContext);
  const userName = user ? user.name : "Unknown";
  const userAvatarUrl = user ? user.avatar_url : "";
  const user_id = user ? user.username : "unknown";

  const links: any[] = [
    { name: "Build", href: "/build" },
    { name: "Playground", href: "/" },
    { name: "Gallery", href: "/gallery" },
    // { name: "Data Explorer", href: "/explorer" },
  ];

  const DarkModeToggle = () => {
    return (
      <appContext.Consumer>
        {(context: any) => {
          return (
            <button
              onClick={() => {
                if (context.darkMode === "dark") {
                  context.setDarkMode("light");
                } else {
                  context.setDarkMode("dark");
                }
              }}
              type="button"
              className="flex-shrink-0 bg-primary p-1 text-secondary rounded-full hover:text-secondary focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent"
            >
              <span className="sr-only">Toggle dark mode </span>
              {context.darkMode === "dark" && (
                <MoonIcon className="h-6 w-6" aria-hidden="true" />
              )}
              {context.darkMode === "light" && (
                <SunIcon className="h-6 w-6" aria-hidden="true" />
              )}
            </button>
          );
        }}
      </appContext.Consumer>
    );
  };
  return (
    <Disclosure
      as="nav"
      className="bg-primary text-primary mb-8 border-b border-secondary"
    >
      {({ open }) => (
        <>
          <div className="  px-0 sm:px-0 lg:px-0 ">
            <div className="flex justify-between h-16">
              <div className="flex  lg:px-0 ">
                <div className="flex flex-shrink-0 items-center pt-2">
                  <a className="block  " href="/#">
                    <div className="pt-1 text-lg ml-14     inline-block">
                      <div className=" flex flex-col">
                        <div className="text-base">{meta.title}</div>
                      </div>
                    </div>
                  </a>
                </div>

                <div className="hidden md:ml-6 md:flex md:space-x-6">
                  {/* Current: "border-accent text-gray-900", Default: "border-transparent text-secondary hover:border-gray-300 hover:text-primary" */}
                  {links.map((data, index) => {
                    const isActive = data.href === link;
                    const activeClass = isActive
                      ? "bg-accent  "
                      : "bg-secondary ";
                    return (
                      <div
                        key={index + "linkrow"}
                        className={`text-primary  items-center hover:text-accent  px-1 pt-1 block   text-sm font-medium `}
                      >
                        <Link
                          className="hover:text-accent h-full flex flex-col"
                          to={data.href}
                        >
                          <div className=" flex-1 flex-col flex">
                            <div className="flex-1"></div>
                            <div className="pb-2 px-3">{data.name}</div>
                          </div>
                          <div
                            className={`${activeClass}  w-full h-1 rounded-t-lg `}
                          ></div>
                        </Link>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="flex items-center md:hidden">
                {/* Mobile menu button */}
                <Disclosure.Button className="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-secondary hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-inset focus:ring-accent">
                  <span className="sr-only">Open main menu</span>
                  {open ? (
                    <XMarkIcon className="block h-6 w-6" aria-hidden="true" />
                  ) : (
                    <Bars3Icon className="block h-6 w-6" aria-hidden="true" />
                  )}
                </Disclosure.Button>
              </div>
            </div>
          </div>
        </>
      )}
    </Disclosure>
  );
};

export default Header;
